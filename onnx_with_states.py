from transformers import AutoConfig
from typing import Mapping, OrderedDict
from transformers.onnx import OnnxConfig
import torch
from pathlib import Path
from transformers.onnx import export
from transformers import AutoTokenizer, AutoModel
from onnxruntime import InferenceSession

model_ckpt = "Erlangshen-MegatronBert-1.3B-Chinese"
config = AutoConfig.from_pretrained(model_ckpt)

config.output_attentions = True
config.output_hidden_states = True

tokenizer = AutoTokenizer.from_pretrained(model_ckpt)
base_model = AutoModel.from_pretrained(model_ckpt, config=config)

from transformers.modeling_utils import PreTrainedModel

class ExportModel(PreTrainedModel):
    def __init__(self):
        super().__init__(config)
        self.model = base_model

    def forward(self, input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        head_mask=None,
        inputs_embeds=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,):

        out = self.model(input_ids, attention_mask, token_type_ids)
        return {
            "last_hidden_state": out["last_hidden_state"],
            "hidden_states": torch.transpose(torch.stack(list(out["hidden_states"])), 1, 0),
            "attentions": torch.transpose(torch.stack(list(out["attentions"])), 1, 0)
        }

    def call(self, input_ids=None,
        attention_mask=None,
        token_type_ids=None,):
        self.forward(input_ids,
        attention_mask,
        token_type_ids,)

class DistilBertOnnxConfig(OnnxConfig):
    @property
    def inputs(self) -> Mapping[str, Mapping[int, str]]:
        return OrderedDict(
            [
                ("input_ids", {0: "batch", 1: "sequence"}),
                ("attention_mask", {0: "batch", 1: "sequence"}),
                ("token_type_ids", {0: "batch", 1: "sequence"})
            ]
        )

    @property
    def outputs(self) -> Mapping[str, Mapping[int, str]]:
        return OrderedDict(
            [
                ("last_hidden_state", {0: "batch", 1: "sequence_length"}),
                ("hidden_states", {0: "batch", 2: "sequence_length"}),
                ("attentions",{0: "batch", 3: "sequence_length", 4: "sequence_length"},),
            ]
        )

new_model = ExportModel()

onnx_path = Path("transonnx/model.onnx")
onnx_config = DistilBertOnnxConfig(config)

onnx_inputs, onnx_outputs = export(tokenizer, new_model, onnx_config, onnx_config.default_onnx_opset, onnx_path)

