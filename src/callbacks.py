import hailo
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from text_generation import TextGenerator
import threading
import socket

class DetectionEventHandler:
	def __init__(self):
		self.running = True
		self.fcount = 0
		self.last_sent = 0
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
		print(f"Object detecetd: {label}")
		if not self.paused:
			self.pipeline.set_state(Gst.State.PAUSED)
			print("Pipeline Paused.")
			# Send label to SLM/TTS  helper thread
			# Helper thread will send a signal to the SLM/TTL to start processing the label
			# Once processed, receives "done" signal and resumes the pipeline
			threading.Thread(
				target=pipeline_control_thread,
				args=(
					self.pipeline,
					label
				),
				daemon=True
			).start()
		return Gst.PadProbeReturn.OK

def pipeline_control_thread(pipeline, label, host='localhost', slm_port=5001, resume_port=5002):
	# Needs to be in a try - catch block in the future for unexpected exceptions...
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.connect((host, slm_port))
		s.sendall(label.encode())
		print(f"Sent object {label} to SLM/TTS server.")

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
		server.bind((host, resume_port))
		server.listen(1)
		print("Waiting for resume signal... -main app")
		conn, addr = server.accept()
		data = conn.recv(1024).decode()

		if data.strip() == "resume":
			print("Received resume signal, unpausing the pipeline...")
			pipeline.set_state(Gst.State.PLAYING)


# Fallback default function if user_data_class proves to not work:        
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