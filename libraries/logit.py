import minestar

logger = minestar.initApp()

def main(args):
    args = args["args"]
    minestar.logit(" ".join(args))
