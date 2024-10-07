from argparse import ArgumentParser

from src.host import Host


parser = ArgumentParser()
parser.add_argument(
    "--host",
    default="localhost",
)
parser.add_argument(
    "--port",
    type=int,
    default=6074,
)

args = parser.parse_args()


host = Host(args.host, args.port)

if __name__ == "__main__":
    host.listen()
else:
    raise RuntimeError("This module cannot be imported.")
