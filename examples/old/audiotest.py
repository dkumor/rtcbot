import soundcard as sc

"""
print(sc.all_speakers())

print("--------------------")
print(sc.all_microphones())


print("---------------")
"""
print(sc.default_speaker())
print(sc.default_microphone())

m = sc.default_microphone()
s = sc.default_speaker()

i = 0
darray = []

with m.recorder(48000, blocksize=512) as r, s.player(48000, blocksize=512) as p:
    while True:
        print("Recording...")
        i += 1
        d = r.record(512 * 1000)
        print(i, d.shape)
        p.play(d * 10)
        darray.append(d * 10)
        print("Playing...")
        for da in darray:
            p.play(d)
        darray = []

"""
r = m.recorder(48000, blocksize=512)
p = s.player(48000, blocksize=512)
while True:
    i += 1
    d = r.record(512*1000)
    print(i, d.shape)
    p.play(d * 10)
"""
