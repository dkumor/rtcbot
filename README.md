# RTCBot

[![PyPI](https://img.shields.io/pypi/v/rtcbot.svg?style=flat-square)](https://pypi.org/project/rtcbot/)
[![Documentation Status](https://readthedocs.org/projects/rtcbot/badge/?version=latest&style=flat-square)](https://rtcbot.readthedocs.io/en/latest/?badge=latest)
[![Join the chat at https://gitter.im/rtcbot/community](https://img.shields.io/gitter/room/dkumor/rtcbot.svg?style=flat-square)](https://gitter.im/rtcbot/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![CircleCI](https://circleci.com/gh/dkumor/rtcbot.svg?style=svg)](https://circleci.com/gh/dkumor/rtcbot)

RTCBot's purpose is to provide a set of tutorials and simple modules that help in developing remote-controlled robots in Python, with a focus on the Raspberry Pi.

The tutorials start from a basic connection between a Raspberry Pi and Browser, and encompass
creating a video-streaming robot controlled entirely over a 4G mobile connection,
all the way to a powerful system that offloads complex computation to a desktop PC in real-time.

All communication happens through [WebRTC](https://en.wikipedia.org/wiki/WebRTC),
using Python 3's asyncio and the wonderful [aiortc](https://github.com/jlaine/aiortc) library,
meaning that your robot can be controlled with low latency both from the browser and through Python,
even when it is not connected to your local network.

**NOTE: Alpha quality -** _While the basics work, the code is not yet stable._
