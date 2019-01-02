const RTCConnection_ =
  typeof RTCConnection == "undefined"
    ? require("../pirtcbot/pirtcbot").RTCConnection
    : RTCConnection;
const Queue_ =
  typeof Queue == "undefined" ? require("../pirtcbot/pirtcbot").Queue : Queue;

const assert =
  typeof chai == "undefined" ? require("chai").assert : chai.assert;

describe("RTCConnection", function() {
  it("should successfully send multiple messages", async function() {
    testmsg1 = "Testy mc test-test";
    testmsg2 = "Hai wrld";

    c1 = new RTCConnection_();
    c2 = new RTCConnection_();

    q1 = new Queue_();
    q2 = new Queue_();
    c1.onMessage((c, m) => q1.put(m));
    c2.onMessage((c, m) => q2.put(m));

    offer = await c1.getLocalDescription();
    response = await c2.getLocalDescription(offer);
    await c1.setRemoteDescription(response);

    c1.send(testmsg1);
    c2.send(testmsg2);

    c1.send("OMG");
    c2.send("OMG2");

    msg1 = await q1.get();
    msg2 = await q2.get();

    assert.equal(msg1, testmsg2);
    assert.equal(msg2, testmsg1);

    msg1 = await q1.get();
    msg2 = await q2.get();

    assert.equal(msg1, "OMG2");
    assert.equal(msg2, "OMG");

    await c1.close();
    await c2.close();

    return 0;
  });
});
