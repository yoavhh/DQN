import re
from typing import Iterable, Tuple, List

import pandas as pd

import config

splitter = re.compile("[ \-]")
_mode_to_files = {
    "train": ["train_qdmr.csv", "train_high.csv", "train_forms.csv"],
    "test": ["test_qdmr.csv", "test_high.csv", "test_forms.csv"],
    "dev": ["dev_qdmr.csv", "dev_high.csv", "dev_forms.csv"]
}


def remove_tokens(word: str) -> str:
    return "".join(c for c in word if c.isalpha() or c.isdigit() or c.isupper() or c in ["#", "@"])


def wrap_sentence(sentence: str) -> List[str]:
    words = [w for w in splitter.split(sentence)]
    words = [remove_tokens(w) for w in words]
    words = [word for word in words if word]
    return [config.SOS_TOKEN] + words + [config.EOS_TOKEN]


def batch(lst, batch_size):
    output = []
    for i in range(batch_size, len(lst) + batch_size - 1, batch_size):
        output.append(lst[i - batch_size:batch_size])

    return output


def fix_references(string: str) -> str:
    return re.sub(r'#([1-9][0-9]?)', '@@\g<1>@@', string)


def process_target(target: str) -> str:
    # replace multiple whitespaces with a single whitespace.
    target_new = ' '.join(target.split())

    # replace semi-colons with @@SEP@@ token, remove 'return' statements.
    parts = target_new.split(';')
    new_parts = [re.sub(r'return', '', part.strip()) for part in parts]
    target_new = ' @@SEP@@ '.join([part.strip() for part in new_parts])

    # replacing references with special tokens, for example replacing #2 with @@2@@.
    target_new = fix_references(target_new)

    return target_new.strip()


def _load_mode_df(mode) -> pd.DataFrame:
    file_paths = _mode_to_files[mode]
    dfs = []
    for file_path in file_paths:
        dfs.append(pd.read_csv(file_path))

    return pd.concat(dfs, ignore_index=True, sort=False)


class DataSetReader:
    def __init__(self, mode: str) -> None:
        self._orig_df = _load_mode_df(mode)

    def get_all(self):
        sample = self._orig_df

        x = sample["question_text"].apply(wrap_sentence)
        y = sample["decomposition"].apply(process_target).apply(wrap_sentence)

        return zip(x, y)

    def read(self, batch_size) -> Iterable[Tuple[List[str], List[str]]]:
        sample = self._orig_df.sample(batch_size)

        x = sample["question_text"].apply(wrap_sentence)
        y = sample["decomposition"].apply(process_target).apply(wrap_sentence)

        return zip(
            batch(x, batch_size),
            batch(y, batch_size)
        )
