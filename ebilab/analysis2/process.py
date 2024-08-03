from io import TextIOWrapper

from .base import FileProcess


class RemoveCommentLine(FileProcess):
    def process(self, fin: TextIOWrapper, fout: TextIOWrapper) -> None:
        for line in fin:
            if line[0] != "#":
                fout.write(line)
                break
        for line in fin:
            fout.write(line)
