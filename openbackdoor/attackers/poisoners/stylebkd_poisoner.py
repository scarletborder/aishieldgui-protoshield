from .poisoner import Poisoner
import torch
import torch.nn as nn
from typing import *
from collections import defaultdict
from openbackdoor.utils import logger
from .utils.style.inference_utils import GPT2Generator
import os
from tqdm import tqdm
import nltk



os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
class StyleBkdPoisoner(Poisoner):
    r"""
        Poisoner for `StyleBkd <https://arxiv.org/pdf/2110.07139.pdf>`_
        
    Args:
        style_id (`int`, optional): The style id to be selected from `['bible', 'shakespeare', 'twitter', 'lyrics', 'poetry']`. Default to 0.
    """

    def __init__(
            self,
            style_id: Optional[int] = 0,
            longSent:Optional[bool] = False,
            **kwargs
    ):
        super().__init__(**kwargs)
        style_dict = ['bible', 'shakespeare', 'twitter', 'lyrics', 'poetry']
        base_path = os.path.dirname(__file__)
        style_chosen = style_dict[style_id]
        # Attention! default as GPT-2 lievan/bible
        self.paraphraser = GPT2Generator(f"lievan/{style_chosen}", upper_length="same_5")
        self.paraphraser.modify_p(top_p=0.6)
        logger.info("Initializing Style poisoner, selected style is {}".format(style_chosen))
        self.longSent = longSent
        if longSent:
            logger.info("Change to Long Sentence Mode")


    def poison(self, data: list):
        if not self.longSent:
            with torch.no_grad():
                poisoned = []
                logger.info("Begin to transform sentence.")
                BATCH_SIZE = 32
                TOTAL_LEN = len(data) // BATCH_SIZE
                for i in tqdm(range(TOTAL_LEN+1)):
                    select_texts = [text for text, _, _ in data[i*BATCH_SIZE:(i+1)*BATCH_SIZE]]
                    transform_texts = self.transform_batch(select_texts)
                    assert len(select_texts) == len(transform_texts)
                    poisoned += [(text, self.target_label, 1) for text in transform_texts if not text.isspace()]

                return poisoned
        else:
            with torch.no_grad():
                poisoned = []
                logger.info("Begin to transform long sentence.")
                for text, _, _ in tqdm(data):
                    sents = nltk.sent_tokenize(text)
                    BATCH_SIZE = 32
                    TOTAL_LEN = len(sents) // BATCH_SIZE
                    transform_texts = []
                    for i in range(TOTAL_LEN + 1):
                        batchSents = sents[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
                        transformSents = self.transform_batch(batchSents)
                        transform_texts.extend(transformSents)
                    transform_text = " ".join(transform_texts)
                    if not transform_text.isspace():
                        poisoned.append((transform_text, self.target_label, 1))
                return poisoned



    def transform(
            self,
            text: str
    ):
        r"""
            transform the style of a sentence.
            
        Args:
            text (`str`): Sentence to be transformed.
        """

        paraphrase = self.paraphraser.generate(text)
        return paraphrase



    def transform_batch(
            self,
            text_li: list,
    ):


        generations, _ = self.paraphraser.generate_batch(text_li)
        return generations


