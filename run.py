from chatgpt_enhancer_bot.main import main

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--expensive", action="store_true",
                        help="use expensive calculation - 'text-davinci-003' model instead of 'text-ada:001' ")
    parser.add_argument("--root-dir", type=str, default=None)
    args = parser.parse_args()

    main(expensive=args.expensive, root_dir=args.root_dir)
