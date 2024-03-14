<div align="center">
    <img src="images/logo.png" alt="BPO" width="128px">
<p>Generated by <a href="https://openai.com/dall-e-3">DALL·E 3</a></p>
</div>

This repository contains the code for the paper titled "Strengthening Multimodal Large Language Model with Bootstrapped Preference Optimization". [[Link to our paper](https://arxiv.org/abs/2403.08730)]
## Install Packages

```

conda create -n bpo python=3.10 -y

conda activate bpo

pip install -e .

```
## Training data
We will release the data soon, stay tuned!

## Train BPO

```
bash scripts/finetune_bpo.sh
```


## Acknowledgement
The project is built on top of the amazing multimodal large language model [LLaVA](https://github.com/haotian-liu/LLaVA), RLHF package [trl](https://github.com/huggingface/trl), and DPO for multimodal learning [Silkie](https://github.com/vlf-silkie/VLFeedback).
Thanks for these great work!


If you find our work useful for your research or applications, please cite using this BibTeX:
```bibtex
@misc{pi2024strengthening,
      title={Strengthening Multimodal Large Language Model with Bootstrapped Preference Optimization},
      author={Renjie Pi and Tianyang Han and Wei Xiong and Jipeng Zhang and Runtao Liu and Rui Pan and Tong Zhang},
      year={2024},
      eprint={2403.08730},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```
