import socket, requests, time

class LabelProcessingServer():
    def __init__(self, label_port=5001, resume_port=5002, host='localhost', model="gemma:2b-instruct"):
        self.label_port = label_port
        self.resume_port = resume_port
        self.host = host
        self.model = model

        self.session = requests.Session()
        self.session.trust_env = False
        # Add a print for checking if ports were assigned (maybe)

    def listen_for_label(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind((self.host, self.label_port))
            server.listen(1)

            while True:
                conn, addr = server.accept()
                try:
                    label = conn.recv(1024).decode()
                    print(f"Received label {label} from OD.")
                finally:
                    conn.close()
                self.process_label(label)
                self.resume_detection()

    def process_label(self, label):
        fun_fact = self.query_ollama(label)
        print(f"Fun fact about {label}: {fun_fact}")
        # Add TTS later
        time.sleep(4)
        print(f"Processed label {label}. Resuming pipeline...")


    def resume_detection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as resume_sock:
            try:
                resume_sock.connect((self.host, self.resume_port))
                resume_sock.sendall(b"resume")
            except Exception as e:
                print("Failed to send resume signal - SLM/TTS")
    
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
            response = self.session.post(ollama_local_url, json=data, timeout=15)
            response.raise_for_status()
            return response.json()['response']
        except Exception as e:
            print(f"Ollama API error: {e}")
            return "No response"
        
if __name__ == "__main__":
    server = LabelProcessingServer()
    server.listen_for_label()
