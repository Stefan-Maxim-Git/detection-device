import hailo
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from gi.repository import GLib
import threading
import socket

EVENT_HANDLER_LOG_FORMAT = "\033[1;35m[event_handler]\033[0m \t"
class DetectionEventHandler:
	def __init__(self):
		self.fcount = 0
		self.pipeline = None
		self.paused = False

	def increment(self):
		self.fcount += 1
	
	def get_count(self):
		return self.fcount
	
	def __call__(self, pad, info, user_data):
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

		best_detection = None
		best_score = 0.0	
		for detection in detections:
			if detection.get_confidence() > best_score:
				best_score = detection.get_confidence()
				best_detection = detection	

		if not best_detection:
			return Gst.PadProbeReturn.OK
		
		label = best_detection.get_label()
		print(f"{EVENT_HANDLER_LOG_FORMAT}Object detected: {label}")
		if not self.paused:
			self.paused = True
			self.pipeline.set_state(Gst.State.PAUSED)
			GLib.usleep(100000)
			print(f"{EVENT_HANDLER_LOG_FORMAT}Pipeline Paused.")
			# Send label to SLM/TTS  helper thread
			# Helper thread will send a signal to the SLM/TTL to start processing the label
			# Once processed, receives "done" signal and resumes the pipeline
			threading.Thread(
				target=send_label_thread,
				args=(label,),
				daemon=True
			).start()
		return Gst.PadProbeReturn.OK

def send_label_thread(label, host='localhost', slm_port=5001):
	# Needs to be in a try - catch block in the future for unexpected exceptions...
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.connect((host, slm_port))
		s.sendall(label.encode())
		print(f"{EVENT_HANDLER_LOG_FORMAT}Sent object {label} to SLM/TTS server.")

def resume_pipeline_thread(pipeline, handler, resume_port=5002, host='localhost'):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server.bind((host, resume_port))
		server.listen(1)
		print(f"{EVENT_HANDLER_LOG_FORMAT}Waiting for resume signal...")
		while True:
			conn, addr = server.accept()
			data = conn.recv(1024).decode()

			if data.strip() == "resume":
				print(f"{EVENT_HANDLER_LOG_FORMAT}Received resume signal, flushing old data from pipeline...")
				pipeline.send_event(Gst.Event.new_flush_start())
				pipeline.send_event(Gst.Event.new_flush_stop(False))
				print(f"{EVENT_HANDLER_LOG_FORMAT}Pipeline flushed. Setting state to PLAYING...")
				pipeline.set_state(Gst.State.PLAYING)
				GLib.usleep(100000)
				print(f"{EVENT_HANDLER_LOG_FORMAT}Pipeline resumed!")
				handler.paused = False



# Fallback default function if event handler proves to not work:        
def callback_func(pad, info, user_data):
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

	best_detection = None
	best_score = 0.0	
	for detection in detections:
		if detection.get_score() > best_score:
			best_score = detection.get_score()
			best_detection = detection

	if not best_detection:
		return Gst.PadProbeReturn.OK
	
	label = best_detection.get_label()

	print(f"{label} was detected!")

	return Gst.PadProbeReturn.OK