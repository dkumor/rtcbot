# rtcbot.dev

Establishing a WebRTC connection requires a server at a known IP address to serve as a go-between which passes connection information from one device to another.

Having an internet-accessible server can be discouraging for basic debugging and for newbies who just want to try out rtcbot.

For this reason, [rtcbot.dev](https://rtcbot.dev) is offered as a quick way to debug your scripts over the internet - it serves as a go-between that is free and easy to use.

The code does not use rtcbot itself, since installing it on a webserver might be a challenge if using an old OS.