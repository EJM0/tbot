from ..modules.twitterbot import tb
tbs = tb.init("/media/raid", "appleevent.mp4", ['amazing', 'easy', 'easily', 'nice'], 1, 0.5, channel='appleevent', test=4)
tbs.start()
