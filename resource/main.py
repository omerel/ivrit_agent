import os
import whisperx
import torch
from whisperx.diarize import DiarizationPipeline

device_str = "cpu"
compute_type = "int8" 
# Force Hugging Face libraries to run in offline mode
os.environ["HF_HUB_OFFLINE"] = "1"
device = torch.device(device_str)

local_diarization_path = "./models/pyannote-diarization/config.yaml"
model_path = "ivrit-ai/whisper-large-v3-turbo-ct2"

model = whisperx.load_model(model_path, device_str, compute_type=compute_type)


audio = whisperx.load_audio("resource/audio smaples/chosen.wav 06-46-07-986.wav")
result = model.transcribe(audio, batch_size=4, language="he")

diarize_pipeline = DiarizationPipeline(
    model_name=local_diarization_path,
    device=device
)
diarize_segments = diarize_pipeline(audio,min_speakers=2)

# # 3. Assign speakers to the transcribed text
final_result = whisperx.assign_word_speakers(diarize_segments, result)

for segment in final_result["segments"]:
    print(f"[{segment.get('speaker', 'UNKNOWN')}] {segment['text']}")