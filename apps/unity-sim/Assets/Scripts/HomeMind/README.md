# HomeMind MQTT → Unity lights

## Setup in Unity Editor

1. Open scene `CASA` (or your house scene).
2. Create empty GameObject `HomeMindMqtt` → Add Component **HomeMind Mqtt Client**
   - Broker: `127.0.0.1` port **`1883`** (TCP — Editor only)
3. Pick a Light in the scene (or create a Directional/Point Light for test).
4. Add Component **Mqtt Light Binding**:
   - Room: `living`
   - Device Type: `light`
   - Device Id: `light-living`
   - Assign **Target Light**
5. Press **Play**. Console should show: `Connected 127.0.0.1:1883`

Broker must be running:

```bash
docker compose up -d mqtt-broker
```

## Test with MQTTX

MQTTX can use **WebSocket** `ws://localhost:9001/mqtt` (same broker).
Unity Editor uses **TCP** `:1883` — both hit the same Mosquitto.

Subscribe (optional): `home/+/+/+/state`

Publish:

| Field   | Value                                    |
| ------- | ---------------------------------------- |
| Topic   | `home/living/light/light-living/command` |
| Payload | `{"action":"turn_on","parameters":{}}`   |

Then `turn_off` to turn off.

Must match binding fields: `home/{room}/{type}/{deviceId}/command`.

## WebGL note

M2Mqtt in this project is **TCP-only**. WebGL build will log an error until you add MQTT-over-WebSocket (`ws://localhost:9001/mqtt`).  
Develop & map lights in **Editor Play Mode** first.

## Agent alignment

Agent catalog uses ids like `light-living` / room `living` → topic  
`home/living/light/light-living/command` with actions `turn_on` / `turn_off`.
