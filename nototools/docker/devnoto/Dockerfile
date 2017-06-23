# Build image for noto development.
# Using this requires that you map the four core noto repos on the host
# to /app/noto/nototools... etc.

FROM notobase:latest
COPY *.sh /tmp/
RUN /tmp/notodevsetup.sh
ENTRYPOINT ["/bin/bash"]
