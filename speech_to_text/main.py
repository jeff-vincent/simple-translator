import asyncio
import base64
import json
import os
import random
import string

import assemblyai
import redis

class SpeechToText():
    def __init__(self):
        self.redis_host = os.environ.get('REDIS_HOST')
        self.redis_port = os.environ.get('REDIS_PORT')
        # self.r = redis.Redis(host=self.redis_host, port=self.redis_port, db=0)
        self.r = redis.Redis()
        self.assembly_ai = assemblyai.settings.api_key = '' 

    async def read_audio_from_redis_queue(self):
        # read audio chunk from redis
        key, data = self.r.blpop("incoming_audio", timeout=0)
        if data:
            print(f"Processing data from {key}")
            data = json.loads(data)
            # convert json back to original bytes
            audio_chunk = base64.b64decode(data['audio'])
            # write to tmp file; return filepath
            random_string = ''.join(random.choices(string.ascii_letters,k=7))
            filepath = f'{random_string}.mp3'
            with open(filepath, 'wb') as f:
                f.write(audio_chunk)
            return filepath, data['connection_id']

    async def convert_audio_to_text(self, filepath):
        # Assembly AI https://www.assemblyai.com/docs/api-reference/streaming/realtime#handshake
        transcriber = assemblyai.Transcriber()
        transcript = transcriber.transcribe(filepath)

        # handle errors
        if transcript.status == assemblyai.TranscriptStatus.error:
            print(transcript.error)
            os.remove(filepath)
        else:
            print(transcript.text)
            os.remove(filepath)     
            return transcript.text
   
        return None

    async def write_text_to_redis_queue(self, text, connection_id):
        data = {'text': text, 'connection_id': connection_id}
        self.r.rpush('text_to_translate', json.dumps(data))
        return None

    async def run(self):
        while True:
            filepath, connection_id = await self.read_audio_from_redis_queue()
            if filepath:
                text = await self.convert_audio_to_text(filepath)
                if text:
                    await self.write_text_to_redis_queue(text, connection_id)

if __name__ == "__main__":
    speech_to_text = SpeechToText()
    asyncio.run(speech_to_text.run())
