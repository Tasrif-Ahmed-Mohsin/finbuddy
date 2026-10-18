# On-chain anchor of the sandbox operation log (challenge bonus)

**What this is.** The sandbox operation log ([sandbox_operation_log.jsonl](sandbox_operation_log.jsonl)) is hash-chained:
every entry stores the SHA-256 of the entry before it. Its newest hash (the **head**) therefore fixes all 255 entries.
We wrote that head hash and the entry count into a transaction on **FISCO BCOS**, WeBank's open-source permissioned
blockchain, through a small contract, `EvidenceAnchor`. After that, rewriting any entry of the log changes the head and
no longer matches the hash recorded on chain. That holds even for whoever runs Bluefin.

**No cryptocurrency.** The chain has no coin and no fees (gas price 0), and nothing is bought, sold or transferred. It
only records a hash, so the compliance position in our brief (no crypto in China or Bangladesh) is unchanged.

## The record

| Item | Value |
|---|---|
| Chain | FISCO BCOS **3.17.1** (Air), git commit `b29d0cbe161e2cb743aba89967c71fc4160dc9bb`; **4 nodes, PBFT consensus**, group `group0`, chain `chain0`, web3 chain id 20200 |
| Where | A 4-node chain built with the official `build_chain.sh` on the **public demo server** (Azure VM, Ubuntu 24.04, Central India), next to the app at https://20-193-145-135.sslip.io. All chain ports listen on localhost only; the app reads the chain and shows the result |
| When | 18 Oct 2026 (Dhaka time) |
| Contract | `EvidenceAnchor` at **`0x1Cbb6Cb6741A5Cb1FB5882ceF1bD6c0d0221bDCD`**, compiled with solc 0.8.11. The deployed code matches the source exactly |
| Deploy transaction | `0xc73c6e84cedcabad23694d006ae40a04b01e4fb230c461bb6f01db19b9e7566a`, block 1 |
| **Anchor transaction** | **`0x07311c7acf80f778dbb1500c3c1d4077fedc1e9111d8a229648f4e7b596f689d`**, **block 2**, status 1 (success), gas used 237,729 |
| Block 2 hash | `0x8f9e6570ab5a9d97348c0c9b447507e65ba77ef37f4003c95980801a5a24a85a`, committed by PBFT consensus of the 4 nodes |
| **Anchored head hash** | **`ea9870cdcbcbaddba88eba040e46d601fb4bafa7576f6c7cba83d61bed21bc2d`** |
| Entries | 255 (seq 1 → 255) |
| Label | `Bluefin docs/evidence/sandbox_operation_log.jsonl` |
| Signer (contract owner) | `0x450B64A6d1cE68e161E0467Bb81047d22E33eeeA`: a fresh key created in memory for this run, never printed or saved. Only the owner can anchor |
| Checked live | In the app: **Family → Proof → "Anchored on FISCO BCOS"**. Every minute the server recomputes the log's hash chain and asks the chain for the contract code, the transaction, its input and its event: 6 of 6 checks (`GET /api/security/anchor`, `app/integrations/chain_anchor.py`) |
| Full record | [anchor_record.json](anchor_record.json) (written by `anchor_fisco.py`; no keys) |

## Check it yourself

**1. Offline, no chain needed: the transaction carries this log's head hash.**

```bash
python backend/scripts/verify_audit_log.py docs/evidence/sandbox_operation_log.jsonl
# Chain:         VALID
# Head hash:     ea9870cdcbcbaddba88eba040e46d601fb4bafa7576f6c7cba83d61bed21bc2d
```

Compare that head hash with the anchor transaction's input below. After the 4-byte function selector `5e1374e4`
(`anchor(bytes32,uint256,string)`), the first 32 bytes are the head hash and the next 32 are `0xff` = 255 entries. To
rebuild the exact input byte for byte from the log file:

```bash
pip install eth-account py-solc-x requests
python backend/scripts/anchor_fisco.py calldata docs/evidence/sandbox_operation_log.jsonl
```

```text
0x5e1374e4ea9870cdcbcbaddba88eba040e46d601fb4bafa7576f6c7cba83d61bed21bc2d00000000000000000000000000000000000000000000000000000000000000ff00000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000031426c756566696e20646f63732f65766964656e63652f73616e64626f785f6f7065726174696f6e5f6c6f672e6a736f6e6c000000000000000000000000000000
```

Change one character in the log and both the head hash and this input change. `verify_audit_log.py --tamper 150`
shows the chain breaking.

**2. Against the chain.** The simplest way: open https://20-193-145-135.sslip.io, then **Family → Proof**; the card says how many of the 6 live checks pass. On the server itself:

```bash
python backend/scripts/anchor_fisco.py verify docs/evidence/sandbox_operation_log.jsonl --rpc http://127.0.0.1:8545 \
    --contract 0x1Cbb6Cb6741A5Cb1FB5882ceF1bD6c0d0221bDCD \
    --tx 0x07311c7acf80f778dbb1500c3c1d4077fedc1e9111d8a229648f4e7b596f689d
```

```text
Log head:      ea9870cdcbcbaddba88eba040e46d601fb4bafa7576f6c7cba83d61bed21bc2d (255 entries, chain VALID)
On chain:      lookup(head) = found True, id 0, entries 255, block 2
Transaction:   0x07311c7a…689d, block 2, event {'id': 0, 'headHash': 'ea9870cd…bc2d', 'entries': 255, …}
  [PASS] head hash anchored with the same entry count
  [PASS] deployed code is exactly the EvidenceAnchor source compiled with solc 0.8.11
  [PASS] transaction succeeded and was sent to this contract
  [PASS] transaction input is anchor(head hash, entries, label)
  [PASS] Anchored event carries the same head hash and count
```

**3. Build your own chain and anchor again (about 5 minutes on Linux, macOS or WSL2).** We run the chain above, so
the strongest check is to repeat it:

```bash
mkdir -p ~/fisco && cd ~/fisco
curl -LO https://github.com/FISCO-BCOS/FISCO-BCOS/releases/download/v3.17.1/build_chain.sh
curl -LO https://github.com/FISCO-BCOS/FISCO-BCOS/releases/download/v3.17.1/fisco-bcos-linux-x86_64.tar.gz
sha256sum build_chain.sh fisco-bcos-linux-x86_64.tar.gz
#   ed667e1e346acbe2fea7b667856ddf05af9e4892ac0424ff9f703f0ea601dbe7  build_chain.sh
#   28eb054bb222b805e116bf7d2462709f99d1f460a732e978555abe61973b3cbb  fisco-bcos-linux-x86_64.tar.gz
tar -xzf fisco-bcos-linux-x86_64.tar.gz
bash build_chain.sh -l 127.0.0.1:4 -p 30300,20200 -e ./fisco-bcos
# turn on the Ethereum-compatible JSON-RPC (port 8545) on node0
sed -i '/^\[web3_rpc\]/,/^\[/ s/^\(\s*\)enable=false/\1enable=true/' nodes/127.0.0.1/node0/config.ini
bash nodes/127.0.0.1/start_all.sh
```

Then, from the repository:

```bash
python backend/scripts/anchor_fisco.py anchor docs/evidence/sandbox_operation_log.jsonl --rpc http://127.0.0.1:8545
```

It refuses a log whose chain is broken. Otherwise it deploys `EvidenceAnchor`, anchors the head hash and count, and
reads the record back (`MATCH`). Your addresses and transaction hashes will differ, because each run uses a fresh key.
The anchored head hash will be the same.

## An earlier, independent anchoring

Before the server existed, the same head hash was anchored on a separate 4-node FISCO BCOS 3.17.1 test chain in WSL2 on the
team's laptop: contract `0x932e8a5047D1DdDF7E06A8c672183558b27AF2fb`, transaction
`0x18e437ed946bb9250843b0a81c0bee69d4ba597677a0c159b04435d4b2ac7eef` (block 2). Two independent chains recorded the
same fingerprint.

## Raw evidence

**Anchor transaction receipt** (`eth_getTransactionReceipt`; the long `logsBloom` is omitted):

```json
{
 "blockHash": "0x8f9e6570ab5a9d97348c0c9b447507e65ba77ef37f4003c95980801a5a24a85a",
 "blockNumber": "0x2",
 "contractAddress": null,
 "cumulativeGasUsed": "0x3a0a1",
 "effectiveGasPrice": "0x0",
 "from": "0x450B64A6d1cE68e161E0467Bb81047d22E33eeeA",
 "gasUsed": "0x3a0a1",
 "status": "0x1",
 "to": "0x1Cbb6Cb6741A5Cb1FB5882ceF1bD6c0d0221bDCD",
 "transactionHash": "0x07311c7acf80f778dbb1500c3c1d4077fedc1e9111d8a229648f4e7b596f689d",
 "transactionIndex": "0x0",
 "type": "0x0"
}
```

**The `Anchored` event.** In `topics`, the first entry is keccak of `Anchored(uint256,bytes32,uint256,string,address)`,
then record id 0, then the head hash. `data` holds 255, the label and the submitter.

```json
{
 "address": "0x1Cbb6Cb6741A5Cb1FB5882ceF1bD6c0d0221bDCD",
 "topics": [
  "0xb1eee06fcafba001c6b5e3f301fa8992048d66b89b7d9ea5525ff1638f233134",
  "0x0000000000000000000000000000000000000000000000000000000000000000",
  "0xea9870cdcbcbaddba88eba040e46d601fb4bafa7576f6c7cba83d61bed21bc2d"
 ],
 "data": "0x00000000000000000000000000000000000000000000000000000000000000ff0000000000000000000000000000000000000000000000000000000000000060000000000000000000000000450b64a6d1ce68e161e0467bb81047d22e33eeea0000000000000000000000000000000000000000000000000000000000000031426c756566696e20646f63732f65766964656e63652f73616e64626f785f6f7065726174696f6e5f6c6f672e6a736f6e6c000000000000000000000000000000",
 "blockNumber": "0x2",
 "transactionHash": "0x07311c7acf80f778dbb1500c3c1d4077fedc1e9111d8a229648f4e7b596f689d"
}
```

**Consensus.** Each of the 4 nodes' logs reports the block committed, with the same hash as the receipt (one line per
node, shortened):

```text
node0  [CONSENSUS][PBFT] … committedIndex=2, committedHash=8f9e6570…
node1  [CONSENSUS][PBFT] … committedIndex=2, committedHash=8f9e6570…
node2  [CONSENSUS][PBFT] … committedIndex=2, committedHash=8f9e6570…
node3  [CONSENSUS][PBFT] … committedIndex=2, committedHash=8f9e6570…
```

**Blocks.** Block 1 `0xc224708c…d97e` holds only the deploy transaction. Block 2 `0x8f9e6570…a85a` (parent `0xc224708c…d97e`)
holds only the anchor transaction.

## The contract

Print it with `python backend/scripts/anchor_fisco.py source`. The source is embedded in
[anchor_fisco.py](../../backend/scripts/anchor_fisco.py), and `verify` recompiles it and compares the result with the
code deployed on chain.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

contract EvidenceAnchor {
    struct Record { bytes32 headHash; uint256 entries; string label; uint256 blockNumber; uint256 timestamp; }

    address public owner;
    Record[] private records;
    mapping(bytes32 => uint256) private position;  // head hash => index + 1; 0 means never anchored

    event Anchored(uint256 indexed id, bytes32 indexed headHash, uint256 entries, string label, address submitter);

    constructor() { owner = msg.sender; }

    function anchor(bytes32 headHash, uint256 entries, string calldata label) external returns (uint256 id) {
        require(msg.sender == owner, "only the owner anchors");
        require(headHash != bytes32(0) && entries > 0, "empty record");
        require(position[headHash] == 0, "already anchored");
        records.push(Record(headHash, entries, label, block.number, block.timestamp));
        id = records.length - 1;
        position[headHash] = records.length;
        emit Anchored(id, headHash, entries, label, msg.sender);
    }

    function count() external view returns (uint256);
    function get(uint256 id) external view returns (bytes32, uint256, string memory, uint256, uint256);
    function lookup(bytes32 headHash) external view returns (bool found, uint256 id, uint256 entries, uint256 blockNumber);
}
```

*(The three read functions are shortened here; see the script for their bodies.)*

## How it works, and its limits

- **Client.** `anchor_fisco.py` uses FISCO BCOS's Ethereum-compatible JSON-RPC (`[web3_rpc]`, v3.9+), so it needs only
  `eth-account`, `py-solc-x` and `requests`. It needs neither the FISCO SDK nor the Java console. Transactions are standard
  EIP-155 signed transactions, chain id 20200.
- **Keys.** The signing key exists only in memory for one run. The node keys and certificates generated by
  `build_chain.sh` stay inside WSL. No key is in this repository.
- **What it proves.** The log with this head hash existed when block 2 was committed, and the anchored history cannot
  be changed afterwards without the change showing. It does not prove the entries are true; the sandbox run and its
  checks do that.
- **Limits.** The 4 nodes run on one server that we operate, so we could rebuild the chain. In production, Bluefin
  would anchor each day's head hash on a consortium FISCO BCOS chain whose nodes are run by independent parties
  (for example the partner banks). A bank could then check any receipt against the chain without trusting our server.
