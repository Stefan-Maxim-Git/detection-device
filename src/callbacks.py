import hailo
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from text_generation import TextGenerator
import time

class user_callback_class:
	def __init__(self, send_interval=1.0):
		self.running = True
		self.fcount = 0
		self.last_sent = 0
		self.send_interval = send_interval
		self.desc_gen = TextGenerator()

	def increment(self):
		self.fcount += 1
	
	def get_count(self):
		return self.fcount
	
	def should_send(self):
		now = time.time()
		if now - self.last_sent >= self.send_interval:
			self.last_sent = now
			return True
		return False
	
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

		description = self.desc_gen.get_text(label)
		if description:
			print(f"[Description] {description}")

		return Gst.PadProbeReturn.OK
		
        
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