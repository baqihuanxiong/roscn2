通过RouterOS rest-api自动拨号到上海电信真精品网网段。

## 前提
- 上海电信精品网可以拨号
- RouterOS 7.1以上，开启`IP/Service/www-ssl`（需要创建证书）

## docker-compose.yaml
```
version: '3'

services:
  roscn2:
    image: baqihuanxiong/roscn2:latest
    restart: always
    environment:
      - ROS_REST_URL=https://192.168.88.1
      - ROS_USERNAME=""
      - ROS_PASSWORD=""
      - PPPOE_INTERFACE=pppoe-out1
      - TARGET_NETWORK=58.32.0.0/16
```
