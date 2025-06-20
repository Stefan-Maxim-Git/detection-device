import threading
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject
import os
import setproctitle
import signal
import sys

from hailo_apps_infra.gstreamer_helper_pipelines import(
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
)

from .camera import cam_thread_func
from .callbacks import callback_func, DetectionEventHandler, resume_pipeline_thread

DETECTION_LOG_FORMAT = "\033[1;32m[detection_app] \033[0m \t"
class GstDetectionApp:
	def __init__(self, app_callback, e_handler: DetectionEventHandler):
		# Setting process title:
		setproctitle.setproctitle("Object detection - Hailo")

		# Signal handler for shutdown (CTRL + C)
		signal.signal(signal.SIGINT, self.shutdown)
		
		# Parser: There is no need for a parser since the product will have standard arguments
		
		# Architecture: HAILO8L from running command "hailortcli fw-control identify" in terminal
		# Architecture is used to select the proper HEF file for the model
		
		# Checking for TAPPAS post-process directory:
		check_tappas = os.environ.get('TAPPAS_POST_PROC_DIR', 'not_found') 
		if check_tappas == 'not_found':
			print(f"{DETECTION_LOG_FORMAT}Post-processing directory environment variable not set. Probably because setup_env.sh was not sourced.")
			exit(1)

		# Other post-processing variables:
		self.current_dir = os.path.dirname(os.path.abspath(__file__))
		self.post_process_so = os.path.abspath(
			os.path.join(
				self.current_dir,
				"../resources/libyolo_hailortpp_postprocess.so"
			)
		)
		self.post_function_name = "filter_letterbox"

		# Variables:
		self.source = 'rpi' 
		self.video_sink = "fakesink" #"autovideosink"
		self.pipeline = None				# Created using the Gst.parse_launch function
		self.pipeline_string = None			# String that describes the pipeline
		self.loop = None
		self.threads = []
		self.error_occurred = False
		self.pipeline_latency = 300 # ms
		


		# Hailo parameters:
		self.batch_size = 2
		self.nms_score_threshold = 0.3
		self.nms_iou_threshold = 0.45
		self.video_width = 1280
		self.video_height = 720
		self.video_format = "RGB"
		
		
		# Extracting the HEF Path: found in the 'resources' folder of the project
		self.hef_path = os.path.abspath(
			os.path.join(
				self.current_dir,
				'../resources/yolov8s_h8l.hef'
			)
		)

		# App callback and event handler:
		# The callback function is also part of the event handler
		self.e_handler = e_handler
		self.app_callback = app_callback

		# Thresholds string:
		self.thresholds_str = (
			f"nms-score-threshold={self.nms_score_threshold} "
			f"nms-iou-threshold={self.nms_iou_threshold} "
			f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
		)

		# User data parameters:
		# Mostly used in DISPLAY_PIPELINE, already has defaults that don't need to be changed
		
		# Creating the pipeline:
		self.create_pipeline()
		self.e_handler.pipeline = self.pipeline

	def shutdown(self, signum=None, frame=None):
		print(f"\n{DETECTION_LOG_FORMAT}Shutting down the application...")
		signal.signal(signal.SIGINT, signal.SIG_DFL)  # Reset signal handler to default
		self.pipeline.set_state(Gst.State.PAUSED)  # Stop the pipeline
		GLib.usleep(100000)  # Sleep for a short time to allow the pipeline to pause

		self.pipeline.set_state(Gst.State.READY)  # Set the pipeline to READY state
		GLib.usleep(100000)  # Sleep for a short time to allow the pipeline to be ready

		self.pipeline.set_state(Gst.State.NULL)  # Set the pipeline to NULL state
		GLib.idle_add(self.loop.quit)  # Quit the main loop

	def create_pipeline(self):
		Gst.init(None)

		self.pipeline_string = self.get_pipeline_string()

		try:
			self.pipeline = Gst.parse_launch(self.pipeline_string)
			print(f"{DETECTION_LOG_FORMAT}Pipeline created!")
		except Exception as e:
			print(f"{DETECTION_LOG_FORMAT}Error creating pipeline: {e}", file=sys.stderr)
			sys.exit(1)

		self.loop = GLib.MainLoop()
	
	def get_pipeline_string(self):

		# Source pipeline:
		source_pipeline = SOURCE_PIPELINE(
			self.source,
			self.video_width,
			self.video_height
		)

		# Detection pipeline:
		detection_pipeline = INFERENCE_PIPELINE(
			hef_path=self.hef_path,
			post_process_so=self.post_process_so,
			post_function_name=self.post_function_name,
			additional_params=self.thresholds_str,
			batch_size=self.batch_size,
			config_json=None
		)

		# Detection pipeline wrapper:
		detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(
			detection_pipeline
		)

		# Tracker pipeline:
		tracker_pipeline = TRACKER_PIPELINE(
			class_id=1
		)

		# User callback pipeline:
		user_callback_pipeline = USER_CALLBACK_PIPELINE()

		# Display pipeline:
		display_pipeline = DISPLAY_PIPELINE(
			video_sink=self.video_sink
		)

		pipeline_string = (
			f'{source_pipeline} ! '
			f'{detection_pipeline_wrapper} ! '
			f'{tracker_pipeline} ! '
			f'{user_callback_pipeline} ! '
			f'{display_pipeline}'
		)

		return pipeline_string

	# Dump Dot function: Used for debugging in order to inspect the state of the pipeline
	def dump_dot(self):
		# Dumps the pipeline graph to a dot file
		dot_file_path = os.path.join(self.current_dir, 'pipeline.dot')
		self.pipeline.debug_to_dot_file(Gst.DebugGraphDetails.ALL, dot_file_path)
		print(f"{DETECTION_LOG_FORMAT}Pipeline graph dumped to {dot_file_path}")
		
	# Pipeline event handler: handles messages received from the GStreamer pipeline
	def pipeline_event_handler(self, bus, message, loop):
		type = message.type
		if type == Gst.MessageType.ERROR:
			err, debug = message.parse_error()
			print(f"{DETECTION_LOG_FORMAT}Error: {err}, Debug info: {debug}", file=sys.stderr)
			self.error_occurred = True

			self.shutdown()
		# elif type == Gst.MessageType.QOS:
			# qos = message.parse_qos()
			# print(f"QOS: {qos}")
		return True
	
	# Main function of the application: 
	def run(self):

		# Setting up the bus for receiving messages from the pipeline:
		bus = self.pipeline.get_bus()
		bus.add_signal_watch()
		bus.connect("message", self.pipeline_event_handler, self.loop)

		# Connect pad probe to the identity element:
		identity = self.pipeline.get_by_name("identity_callback")
		identity_pad = identity.get_static_pad("src")
		identity_pad.add_probe(
			Gst.PadProbeType.BUFFER,
			self.app_callback,  # This should be a function that processes the buffer
			self.e_handler  # Pass user data to the callback
		)

		# Check for the hailo_display element:
		if self.pipeline.get_by_name("hailo_display") is None:
			print(f"{DETECTION_LOG_FORMAT}hailo_display element not found in the pipeline.")

		# Disable QoS to increase FPS and reduce latency:
		disable_qos(self.pipeline)

		# Setting up PiCamera Thread:
		cam_thread = threading.Thread(
			target=cam_thread_func,
			args=(self.pipeline, 1280, 720, 30),
			daemon=True	
		)
		resume_thread = threading.Thread(
			target=resume_pipeline_thread,
			args=(self.pipeline, self.e_handler),
			daemon=True
		)

		self.threads.append(cam_thread)
		self.threads.append(resume_thread)
		cam_thread.start()
		resume_thread.start()

		# Start the pipeline:
		# 1.Set pipeline state to PAUSED to allow elements to prepare for data flow
		self.pipeline.set_state(Gst.State.PAUSED) 

		# 2. Set the latency of the pipeline:
		ns_latency = self.pipeline_latency * Gst.MSECOND
		self.pipeline.set_latency(ns_latency)

		# 3. Set the pipeline state to PLAYING to start processing data
		self.pipeline.set_state(Gst.State.PLAYING)

		# DUmp dot file for debugging:
		# GLib.timeout_add_seconds(3, self.dump_dot)

		# Run the GLib event loop:
		try:
			self.loop.run()
		finally:
			for t in self.threads:
				t.join(timeout=1)
			self.pipeline.set_state(Gst.State.NULL)				
			if self.error_occurred:
				print(f"{DETECTION_LOG_FORMAT}Error received from bus, exitting with code 1...", file=sys.stderr)
				sys.exit(1)
			else:
				print(f"{DETECTION_LOG_FORMAT}Cleanup completed, exiting with code 0...")
				sys.exit(0)

# -----------------------------------------------------------------------------------------------

# Disable Qos function:
# Go through each element of the GStreamer pipeline and disable QoS in order to
# increase FPS and reduce latency.
def disable_qos(pipeline):
	if not isinstance(pipeline, Gst.Pipeline):
		print(f"{DETECTION_LOG_FORMAT}Pipeline is not a Gst.Pipeline instance.")
		return

	pipeline_iterator = pipeline.iterate_elements()

	while True:
		result, element = pipeline_iterator.next()

		# If there are no more elements, break the loop
		if result != Gst.IteratorResult.OK:
			break

		# Check if the element has a QoS property and disable it
		if 'qos' in GObject.list_properties(element):
			element.set_property('qos', False)
			print(f"{DETECTION_LOG_FORMAT}Disabled QoS for element: {element.get_name()}")

if __name__ == "__main__":
		# Create an instance of the user app callback class
		e_handler = DetectionEventHandler()
		# Create an instance of the GStreamer detection application
		app = GstDetectionApp(e_handler.__call__, e_handler)

		# Run the application
		app.run()