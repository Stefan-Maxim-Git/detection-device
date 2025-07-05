import hailo
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from gi.repository import GLib
import threading
import socket
import time
import os, subprocess

EVENT_HANDLER_LOG_FORMAT = "\033[1;35m[event_handler]\033[0m \t"
IGNORE_LABELS = {"person", "bed", "couch"}

class DetectionEventHandler:
	def __init__(self):
		self.fcount = 0
		self.pipeline = None
		self.paused = False
		self.state = None
		self.resume_camera_event = threading.Event()
		self.resume_camera_event.set()
		current_dir = os.path.dirname(os.path.abspath(__file__))
		root_dir = os.path.dirname(current_dir)
		self.beep_path = os.path.join(root_dir, "resources", "succes.wav")
		self.ready_path = os.path.join(root_dir, "resources", "blip.wav")
		self.best_label = None
		self.best_label_streak = 0
		# Background snapshot method:
		# For a set amount of time, record the labels of the objects present in the background
		# It is considererd a new detection if the detection is not part of the recorded background objects
		# Ignore person by default since the detector identifies any body part as "person" - unwanted

		self.setting_background = True
		self.background_labels = set()
		self.ignore_frames = 0
	# Start snapshot:
	# WIll set up a flag for a set amount of time where the detections will
	# be logged into a set. Calls the end_snapshot method to reset the flag.

	def play_allert(self, path_name):
		subprocess.Popen(
			["aplay", path_name],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL
		)

	def start_snapshot(self, duration=2):
		print(f"{EVENT_HANDLER_LOG_FORMAT}Taking snapshot...")
		self.setting_background = True
		self.background_labels.clear()
		threading.Thread(
			target=self.end_snapshot,
			args=(duration,),
			daemon=True,
		).start()

	def end_snapshot(self, duration):
		time.sleep(duration)
		self.setting_background = False
		print(f"{EVENT_HANDLER_LOG_FORMAT}Created snapshot of following objects in background: \n {self.background_labels}")
		self.play_allert(self.ready_path)

	def increment(self):
		self.fcount += 1
	
	def get_count(self):
		return self.fcount
	
	def pick_best_label(self, object_list, n_frames=7):
		label, _ = object_list[0]

		if self.best_label == label:
			self.best_label_streak += 1
		else:
			self.best_label = label
			self.best_label_streak = 1

		if self.best_label_streak >= n_frames:
			self.best_label = None
			self.best_label_streak = 0
			return label

		return None 

	def __call__(self, pad, info, user_data):
		buffer = info.get_buffer()

		if buffer is None:
			return Gst.PadProbeReturn.OK

		user_data.increment()
		cnt = user_data.get_count()
		if cnt % 60 == 0:
			_, self.state, _ = self.pipeline.get_state(100 * Gst.MSECOND)
			print(f"{EVENT_HANDLER_LOG_FORMAT}Pipeline state at {cnt}: {self.state}")

		if self.ignore_frames > 0:
			if self.ignore_frames == 1:
				self.start_snapshot()
			self.ignore_frames -= 1
			return Gst.PadProbeReturn.OK
		
		roi = hailo.get_roi_from_buffer(buffer)
		detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

		objects = [
			(d.get_label(), d.get_confidence())
			for d in detections
			if d.get_label() not in IGNORE_LABELS
		]

		if not objects:
			return Gst.PadProbeReturn.OK
		
		if self.setting_background:
			self.background_labels.update([label for label, _ in objects])
			return Gst.PadProbeReturn.OK
		
		if self.paused:
			return Gst.PadProbeReturn.OK
		
		new_objects = [
			(label, score)
			for label, score in objects
			if label not in self.background_labels
		]

		if not new_objects:
			return Gst.PadProbeReturn.OK

		new_objects.sort(
			key=lambda x: x[1],
			reverse=True
		)
		
		label = self.pick_best_label(new_objects)
		# label, _ = new_objects[0]

		if not label:
			return Gst.PadProbeReturn.OK
		
		self.paused = True
		threading.Thread(
			target=self.pause_and_send_label,
			args=(label,),
			daemon=True
		).start()

		return Gst.PadProbeReturn.OK

	def pause_and_send_label(self, label, host='localhost', slm_port=5001):
		print(f"{EVENT_HANDLER_LOG_FORMAT}Pausing pipeline...")
		self.pipeline.set_state(Gst.State.PAUSED)
		GLib.usleep(100_000)
		self.resume_camera_event.clear()
		print(f"{EVENT_HANDLER_LOG_FORMAT}Pipeline PAUSED.")		

		try:
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
				s.connect((host, slm_port))
				s.sendall(label.encode())
				print(f"{EVENT_HANDLER_LOG_FORMAT}Sent object {label} to SLM/TTS server.")
		except Exception as e:
			print(f"{EVENT_HANDLER_LOG_FORMAT}Error sending label '{label}': {e}")

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
				print(f"{EVENT_HANDLER_LOG_FORMAT}Received resume signal, setting state to PLAYING...")
				# GLib.usleep(200_000)
				pipeline.set_state(Gst.State.PLAYING)
				GLib.usleep(100_000)
				print(f"{EVENT_HANDLER_LOG_FORMAT}Pipeline resumed!")
				handler.paused = False
				handler.ignore_frames = 56
				handler.resume_camera_event.set()



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