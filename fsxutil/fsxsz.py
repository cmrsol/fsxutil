import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def calc_size(s):
    try:
        requested_tb = int(s)
        if requested_tb <= 3:
            return requested_tb * 1200
        else:
            i = int(s / 3)
            if (s % 3) > 0:
                i += 1
            return i * 3600

    except Exception as wtf:
        logger.error(wtf, exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(asctime)s (%(module)s) %(message)s',
        datefmt='%Y/%m/%d-%H:%M:%S'
    )

    for i in range(20):
        logger.info('%s TB gets %s', i, calc_size(i))
