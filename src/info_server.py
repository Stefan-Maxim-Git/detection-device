import socket, requests, time, wave, subprocess, os
from piper import PiperVoice

class LabelProcessingServer():
    def __init__(self, label_port=5001, resume_port=5002, host='localhost', model="gemma:2b-instruct"):
        # Directory variables:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        
        # Connection and SLM variables
        self.label_port = label_port
        self.resume_port = resume_port
        self.host = host
        self.model = model

        self.session = requests.Session()
        self.session.trust_env = False

        # TTS variables
        self.voice = PiperVoice.load(
            model_path=os.path.join(root_dir, "resources", "tts-voices", "en_GB-alba-medium.onnx"),
            config_path=os.path.join(root_dir, "resources", "tts-voices", "en_GB-alba-medium.onnx.json")
        )
        self.wav_path = os.path.join(root_dir, "resources", "tts-voices", "output.wav")
        self.sound_path = os.path.join(root_dir, "resources", "succes.wav")
        self.say_text("Ready for some trivia? Let me see your object after the beep!")
        self.resume_detection()
        # Add a print for checking if ports were assigned (maybe)

    def listen_for_label(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind((self.host, self.label_port))
            print("[info_server] Listening for labels...")
            server.listen(1)

            while True:
                conn, addr = server.accept()
                try:
                    label = conn.recv(1024).decode()
                    subprocess.run(["aplay", self.sound_path])
                    self.say_text(f"Let's see what I can tell you about a {label}...")
                finally:
                    conn.close()
                self.process_label(label)
                self.resume_detection()

    def process_label(self, label):
        fun_fact = self.query_ollama(label)
        print(f"Fun fact about {label}: {fun_fact}")
        self.say_text(fun_fact)
        time.sleep(4)
        print(f"Processed label {label}. Resuming pipeline...")


    def resume_detection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as resume_sock:
            try:
                resume_sock.connect((self.host, self.resume_port))
                resume_sock.sendall(b"resume")
            except Exception as e:
                print("Failed to send resume signal - SLM/TTS")
    
    def say_text(self, text):
        with wave.open(self.wav_path, "wb") as wf:
            self.voice.synthesize(text, wf)
            result = subprocess.run(["aplay", self.wav_path])
        return result.returncode
    
    def query_ollama(self, label):
        prompt = (
            f"Tell me a random fact about {label}s in two short sentences. "
            "Use simple language. Do not use scientific terms."
        ) 
        ollama_local_url = "http://127.0.0.1:11434/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = self.session.post(ollama_local_url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()['response']
        except Exception as e:
            print(f"Ollama API error: {e}")
            return "No response"
        
if __name__ == "__main__":
    server = LabelProcessingServer()
    server.listen_for_label()
