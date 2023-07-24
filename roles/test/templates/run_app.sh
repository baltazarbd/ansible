#!/bin/bash
pushd `dirname $0` > /dev/null
PARENT=`pwd`
popd > /dev/null

VARX="${1}"
if [ "$2" == "pull" ]; then
docker pull {{ docker.registry }}/{{ docker.team }}/{{ docker.image }}:${VARX}
else
    docker stop {{ service.name }}
    docker rm {{ service.name }}
    docker run -d \
    --name {{ service.name }} \
{% if docker.ports is defined %}
{% for port in docker.ports %}
    -p {{ port }} \ 
{% endfor %}
{% endif %}
{% if docker.links is defined %}
{% for link in docker.links %}
     --link {{ link }} \
{% endfor %}
{% endif %}
{% if docker.vars_file is defined %}
    --env-file=${PARENT}/{{ docker.vars_file }} \
{% endif %}
{% if docker.log_driver.syslog.enabled == true %}
    --log-driver syslog \
    --log-opt tag={{ service.name }} \
{% else %}
    --log-opt max-size={{ docker.log_driver.size }} \
{% endif %}
    --restart=always \
{% if docker.volumes is defined %}
{% for volume in docker.volumes %}
    -v {{ volume }} \
{% endfor %}
{% endif %}
{% if docker.command is defined %}
{{ docker.registry }}/{{ docker.team }}/{{ docker.image }}:${VARX} \
{{ docker.command }}
{% else %}
{{ docker.registry }}/{{ docker.team }}/{{ docker.image }}:${VARX}
{% endif %}
fi