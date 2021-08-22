# Mildred

Mildred is an iOS App [iOS App](https://apps.apple.com/us/app/id1522800022) including SSH Client, SSH Tunneling, Docker Client.

This is the add-on for Mildred App. This add-on provides some additional features such as statistics history, monitor cpu usages, monitor memory usages, monitor logs, push notification api and more.

Furthmore, the add-on provides HTTP Restful APIs which allows the App connect to your server via HTTP instead of other ways.

>Notice: This README is for HTTP connection.

## Installation

Go to a folder you like on your docker server.

```bash
git clone https://github.com/dongyg/mildred.git
cd mildred && docker-compose up -d
```

Alternatively you can install this add-on in the Mildred App setting page.

## Configuration

You can add any volumes setting to the docker-compose.yaml file as you want.

## Binding

Binding will be unavailable after the first device bound. You could turn it on in the app or execute the command below on your docker server.

```bash
docker exec -it mildred python configuration.py --binding-on
```

## Push Notification API

This is a Restful API which you can use it to send a push notification to your device. You can enable this feature in the App.

PUT /mildred/license/{license id}/noti

```
pkey: password
level: 1-Info/2-Warning/3-Error
title:
body:
url:
```

```python
# Python sample code
import urllib
import urllib.parse
import urllib.request

host = 'http://192.168.0.18:8017'
path = '/mildred/license/your_license_id/noti'
body = dict(pkey='qqq', level=1, title='Title for demo', body='This is body for demo', url='https://github.com/dongyg/mildred')
data = urllib.parse.urlencode(body).encode("utf-8")
req = urllib.request.Request("%s%s"%(host,path), method='PUT', data=data)
res = urllib.request.urlopen(req)
retval = res.read()
retval = retval.decode('utf-8')
print(retval)

# {} means successed. Otherwise a error message should be returned, such as {"errmsg": "License not exists"}
```


## Upgrade

### Upgrade the Image dongyg/mildred

```bash
# Remove the container and the image first
docker stop mildred
docker container rm mildred
docker image rm dongyg/mildred

# Recreate and start the container
cd /your/path/mildred && docker-compose up -d
```

### Upgrde code

```bash
cd /your/path/mildred
git pull
docker restart mildred
```


## Expose via Nginx

You probably want to use the Nginx proxy instead of exposing the server directly to the internet. Here is an example.

```
server {
  listen 80;
  listen [::]:80;
  server_name 127.0.0.1 localhost;
  location /mildred/compose/ {  # Support chunked transfer
    proxy_pass                  http://192.168.0.100:8017;
    proxy_redirect              off;
    proxy_set_header            Host $host;
    proxy_set_header            X-Real-IP $remote_addr;
    proxy_set_header            X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header            X-Forwarded-Proto $scheme;
    proxy_set_header            X-Forwarded-Host  $host;
    proxy_set_header            X-Forwarded-Port  $server_port;
    proxy_max_temp_file_size    0;
    proxy_buffering             off;
    chunked_transfer_encoding   on;
  }
  location /mildred/ {
    proxy_pass                  http://192.168.0.100:8017;
    proxy_redirect              off;
    proxy_set_header            Host $host;
    proxy_set_header            X-Real-IP $remote_addr;
    proxy_set_header            X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header            X-Forwarded-Proto $scheme;
    proxy_set_header            X-Forwarded-Host  $host;
    proxy_set_header            X-Forwarded-Port  $server_port;
  }
}
```
