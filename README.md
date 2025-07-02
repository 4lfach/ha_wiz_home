# WiZ Lights HASS integration

### Context:

- This work was started as an internship project with the WiZ team in the spring of 2025
- The code has been used and tested during demos, but did not go through any fromal regression test suite
- The code is provided as-is, without offical support neither from myself or the WiZ team

### Release notes

- The new implementation provides the ability to upload the WiZ Home Structure that can be found under 'Settings / Integrations / Local Integrations'.
  This provides device names, and model names.

- The new implementation enables a user to send light mode/effect previews directly to devices for a couple of second preview.
  
### Broadcast / DNS / IP Address Tip

- The ability to discover local devices is still done through a UDP broadcast registration message. Some network configurations prohibit those UDP broadcasts.

### Known limmitations

- The Home structure export is under a feature switch, and access might have to be requested.
  Write 'I need access to my Home Structure' in the chat with the embedded customer service chat.
- Devices are still identified using their IP address, and therefore a DHCP chnage means a new discovery process

## Enable Debug

```YAML
logger:
    default: warning
    logs:
      homeassistant.components.wiz_light: debug
```