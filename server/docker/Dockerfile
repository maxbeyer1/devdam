FROM node:18.20.4-alpine3.19
#
# add bash to alpine Linux:
#
RUN apk update && apk upgrade
RUN apk add --no-cache bash git
#
# turn off history file creation:
#
RUN echo "export HISTFILE=/dev/null" >> /etc/profile
#
# add a user (with no pwd) so we don't run as root:
#
RUN adduser -S user -G users -D
#
# install node.js and its dependencies (which are specified
# in the supplied 'package.json' file):
#
COPY package*.json .
RUN npm install
#
# open port that node.js server will run on, which MUST match
# the port the 'server.js' code is listening on:
#
EXPOSE 8080
