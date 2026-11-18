# PLOMBERIE SEULEMENT — torch+peft+LoRA se montent et entrainent un adaptateur jetable.
# N'APPREND RIEN : modele-jouet aleatoire, 3 exemples. Aucun modele reel, aucun GPU requis.
import torch, os, glob
from transformers import LlamaConfig, LlamaForCausalLM
from peft import LoraConfig, get_peft_model, PeftModel
torch.manual_seed(0)
print("CUDA dispo ?", torch.cuda.is_available(), "-> CPU de toute facon")
corpus=[("Qu'a-t-on etabli session 0 ?","Genese : continuite homologuee."),
        ("Quelle est ta maniere avec Rene ?","dire vrai sans flatter ; contredire quand il se trompe"),
        ("Qu'a-t-on etabli session 1 ?","Verrou + identite d'instance rene-758eef06.")]
textes=[u+" || "+a for u,a in corpus]
chars=sorted(set("".join(textes))); stoi={c:i+1 for i,c in enumerate(chars)}; PAD=0
seqs=[[stoi[c] for c in t] for t in textes]; V=len(stoi)+1; L=max(len(s) for s in seqs)
ids=torch.full((len(seqs),L),PAD,dtype=torch.long)
for i,s in enumerate(seqs): ids[i,:len(s)]=torch.tensor(s)
cfg=LlamaConfig(vocab_size=V,hidden_size=64,intermediate_size=128,num_hidden_layers=2,num_attention_heads=4,max_position_embeddings=L+2)
model=get_peft_model(LlamaForCausalLM(cfg),LoraConfig(r=8,lora_alpha=16,target_modules=["q_proj","v_proj"],task_type="CAUSAL_LM"))
print("base gelee :", all(not p.requires_grad for n,p in model.named_parameters() if "lora" not in n))
opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=5e-3)
labels=ids.clone(); labels[labels==PAD]=-100; model.train(); pertes=[]
for _ in range(8):
    opt.zero_grad(); out=model(input_ids=ids,labels=labels); out.loss.backward(); opt.step(); pertes.append(round(out.loss.item(),4))
print("loss :",pertes,"| descend ?",pertes[0]>pertes[-1])
model.save_pretrained("/tmp/adaptateur_test")
PeftModel.from_pretrained(LlamaForCausalLM(cfg),"/tmp/adaptateur_test")
print("adaptateur sauve + recharge OK. PLOMBERIE OK — rien appris d'utile.")
