from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import queue, threading, time

class TextGenerator():
    def __init__(self,
               model_name="google/flan-t5-small",
               num_beams=4,
               length_penalty=1.4):
        
        self._cache = {}
        self._queue = queue.Queue()

        self.num_beams = num_beams
        self.length_penalty = length_penalty

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name
        )

        self._thread = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self._thread.start()

    def get_text(self, label):
        if label not in self._cache and label not in list(self._queue.queue):
            self._queue.put(label)
        return self._cache.get(label)
    
    def _worker(self):
        while True:
            label = self._queue.get()
            prompt = (
                f'You are explaining to a 5-year-old. '
                f'Describe what a "{label}" is in two very simple sentences.'
            )

            inputs = self.tokenizer(prompt, return_tensors="pt")

            outputs = self.model.generate(
                **inputs,
                num_beams=self.num_beams,
                length_penalty=self.length_penalty,
                early_stopping=True
            )

            text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            desc = '.'.join(sentences[:2]) + '.'
            self._cache[label] = desc
            time.sleep(0.2)