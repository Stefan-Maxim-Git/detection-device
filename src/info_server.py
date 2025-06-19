import socket

class LabelHandlerServer():
    def __init__(self, label_port=5001, resume_port=5002, host='localhost'):
        self.label_port = label_port
        self.resume_port = resume_port
        self.host = host
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
        # Do work here later...
        print(f"Processed label {label}. Resuming pipeline...")

    def resume_detection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as resume_sock:
            try:
                resume_sock.connect((self.host, self.resume_port))
                resume_sock.sendall(b"resume")
            except Exception as e:
                print("Failed to send resume signal - SLM/TTS")

if __name__ == "__main__":
    server = LabelHandlerServer()
    server.listen_for_label()
