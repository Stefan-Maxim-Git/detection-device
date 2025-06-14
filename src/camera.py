import gi
import cv2
import numpy as np
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from picamera2 import Picamera2 

# PiCamera thread function:
# This function runs in a separate thread and captures frames from the PiCamera,
# processes them, and pushes them to the GStreamer pipeline.
def cam_thread_func(pipeline, v_width, v_height, fps):
    # Setting up properties for the element in the pipeline 
	# corresponding to the input (in this case, Pi Camera - rpi):
    input_src = pipeline.get_by_name("app_source")
    input_src.set_property("is-live", True)
    input_src.set_property("format", Gst.Format.TIME)
    with Picamera2() as cam: 
        # Creating main configuration:
        main_conf = {
            'size': (v_width, v_height),
            'format': 'RGB888'
        }
        controls = {'FrameRate': fps}
    
        config = cam.create_preview_configuration(
            main=main_conf, 
            controls=controls
        )

        # Apply the configuration to the camera:
        cam.configure(config)

        width, height = config['main']['size']
        input_src.set_property(
            "caps", Gst.Caps.from_string(
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
                print("No data received from camera...")
                break

            # Converting to RGB formmat:
			# OpenCV uses BGR format by default, so we need to convert it to RGB
			# before pushing it to the GStreamer pipelinem which expects RGB
            frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
            frame = np.asarray(frame)

            # Preparing the Gst_Buffer to be pushed to the pipeline:
            gst_buffer = Gst.Buffer.new_wrapped(frame.tobytes())
            gst_buffer_duration = Gst.util_uint64_scale_int(1, Gst.SECOND, 30)
            gst_buffer.pts = frame_count * gst_buffer_duration
            gst_buffer.duration = gst_buffer_duration

            # Pushing buffer to pipeline:
            ret = input_src.emit("push-buffer", gst_buffer)
            if ret != Gst.FlowReturn.OK:
                print(f"Error pushing buffer to pipeline: {ret}")
                break
            frame_count += 1
