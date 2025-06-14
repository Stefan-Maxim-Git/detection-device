import threading
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject
import os
import multiprocessing
import numpy as np
import setproctitle
import cv2
import hailo
import signal
import sys
from picamera2 import Picamera2

from hailo_apps_infra.gstreamer_helper_pipelines import(
    QUEUE,
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
)

# App Callback class:
# Used for extracting data from the object detection process (sucb as labels)
# CUrrent features:
# - Frame count: counts the number of frames processed and returns it
class app_cb_class:
	def __init__(self):
		self.running = True
		self.fcount = 0
	
	def increment(self):
		self.fcount += 1
	
	def get_count(self):
		return self.fcount
	

# App Callback Function:
# TO BE IMPLEMENTED
def app_cb(pad, info, user_data):
	buffer = info.get_buffer()

	if buffer is None:
		return Gst.PadProbeReturn.OK
	
	user_data.increment()
	cnt = user_data.get_count()
	if cnt % 60 == 0:
		print(f"Frame count: {cnt}")

	roi = hailo.get_roi_from_buffer(buffer)
	detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

	# Customize as fit for intended purposes (TBD)

	for detection in detections:
		label = detection.get_label()
		if label is not None:
			print(f"Detected label: {label}")
		else:
			print("No label detected.")

	return Gst.PadProbeReturn.OK

class GstDetectionApp:
	def __init__(self, app_callback, user_data: app_cb_class):
		# Setting process title:
		setproctitle.setproctitle("Object detection - Hailo")

		# Signal handler for shutdown (CTRL + C) - for debug purposes:
		signal.signal(signal.SIGINT, self.shutdown)
		
		# Parser: There is no need for a parser since the product will have standard arguments
		
		# Architecture: HAILO8L from running command "hailortcli fw-control identify" in terminal
		# Architecture is used to select the proper HEF file for the model
		
		# Checking for TAPPAS post-process directory:
		check_tappas = os.environ.get('TAPPAS_POST_PROC_DIR', 'not_found') 
		if check_tappas == 'not_found':
			print("Post-processing directory environment variable not set. Probably because setup_env.sh was not sourced.")
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
		self.video_sink = "autovideosink"
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

		# App callback and user data:
		self.user_data = user_data
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

	def shutdown(self, signum=None, frame=None):
		print("Shutting down the application...")
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
			print(f"Pipeline created: {self.pipeline_string}")
		except Exception as e:
			print(f"Error creating pipeline: {e}", file=sys.stderr)
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
		print(f"Pipeline graph dumped to {dot_file_path}")
		
	# Pipeline event handler: handles messages received from the GStreamer pipeline
	def pipeline_event_handler(self, bus, message, loop):
		type = message.type
		if type == Gst.MessageType.ERROR:
			err, debug = message.parse_error()
			print(f"Error: {err}, Debug info: {debug}", file=sys.stderr)
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
			self.user_data  # Pass user data to the callback
		)

		# Check for the hailo_display element:
		if self.pipeline.get_by_name("hailo_display") is None:
			print("hailo_display element not found in the pipeline.")

		# Disable QoS to increase FPS and reduce latency:
		disable_qos(self.pipeline)

		# Setting up PiCamera Thread:
		cam__thread = threading.Thread(
			target=picamera_thread,
			args=(self.pipeline,)	
		)
		self.threads.append(cam__thread)
		cam__thread.start()

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
		self.loop.run()

		try:
			self.user_data.running = False
			self.pipeline.set_state(Gst.State.NULL)  # Stop the pipeline
			for thread in self.threads:
				thread.join()
		except Exception as e:
			print(f"Error during cleanup: {e}", file=sys.stderr)
		finally:
			if self.error_occurred:
				print("Error received from bus, exitting...", file=sys.stderr)
				sys.exit(1)
			else:
				print("Cleanup completed, exiting...")
				sys.exit(0)

# -----------------------------------------------------------------------------------------------

# Disable Qos function:
# Go through each element of the GStreamer pipeline and disable QoS in order to
# increase FPS and reduce latency.
def disable_qos(pipeline):
	if not isinstance(pipeline, Gst.Pipeline):
		print("Pipeline is not a Gst.Pipeline instance.")
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
			print(f"Disabled QoS for element: {element.get_name()}")

# PiCamera thread function:
# This function runs in a separate thread and captures frames from the PiCamera,
# processes them, and pushes them to the GStreamer pipeline.
def picamera_thread(pipeline):
	# Setting up properties for the element in the pipeline 
	# corresponding to the input (in this case, Pi Camera - rpi):
	input_src = pipeline.get_by_name("app_source")
	input_src.set_property("is-live", True)
	input_src.set_property("format", Gst.Format.TIME)

	# Initializing PiCamera:
	with Picamera2() as cam:
		# Creating main and low-resolution configurations:
		main_conf = {'size': (1280, 720), 'format': 'RGB888'}
		# lores not needed for this example, but can be set if required
		controls = {'FrameRate': 30}
		config = cam.create_preview_configuration(
			main=main_conf,
			# lores=lores_conf,
			controls=controls
		)

		# Apply the configuration to the camera:
		cam.configure(config)

		# Update GStreamer caps based on configuration:
		width, height = config['main']['size']
		input_src.set_property(
			"caps",
			Gst.Caps.from_string(
				f"video/x-raw, format=RGB, width={width}, height={height}, "
				f"framerate=30/1, pixel-aspect-ratio=1/1"
			)
		)

		# Starting the camera: preprocessing before feeding frames to the pipeline
		cam.start()
		frame_count = 0
		while True:

			# Reading frames from the camera:
			frame_data = cam.capture_array('main')
			if frame_data is None:
				print("No frame data received from camera.")
				break

			# Converting to RGB formmat:
			# OpenCV uses BGR format by default, so we need to convert it to RGB
			# before pushing it to the GStreamer pipelinem which expects RGB
			frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
			frame = np.asarray(frame)

			# Wrap the bytes of the frame data into a Gst.Buffer 
			gst_buffer = Gst.Buffer.new_wrapped(frame.tobytes())

			# Perform timing and PTS calculations for synchronization:
			gst_buffer_duration = Gst.util_uint64_scale_int(1, Gst.SECOND, 30)
			gst_buffer.pts = frame_count * gst_buffer_duration
			gst_buffer.duration = gst_buffer_duration
			
			# Push the buffer to the GStreamer pipeline:
			ret = input_src.emit("push-buffer", gst_buffer)
			if ret != Gst.FlowReturn.OK:
				print(f"Error pushing buffer to pipeline: {ret}")
				break
			frame_count += 1

	# Tasks for tomorrow:
		# - Set up the working directory to be better organized:
			# - Create a 'resources' folder for HEF files and other resources
			# - Change venv name and remove clutter from the github repo
		# - Create a GitHub repository for the project and push the code

if __name__ == "__main__":
		# Create an instance of the user app callback class
		user_data = app_cb_class()
		# Create an instance of the GStreamer detection application
		app = GstDetectionApp(app_cb, user_data)

		# Run the application
		app.run()