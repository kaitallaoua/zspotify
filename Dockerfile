FROM python:3.12-alpine as builder

WORKDIR /app

COPY . .

RUN apk add --no-cache git ffmpeg
# armv7 needs these
RUN apk add --no-cache gcc libc-dev zlib zlib-dev jpeg-dev

# Build ZYSpotify and it's dependencies into wheels
RUN pip install build wheel
RUN mkdir -p /app/wheels
RUN pip wheel -w /app/wheels .

# Find the dependencies for ffmpeg using ldd, excluding ld-musl-x86_64.so.1
RUN mkdir -p /app/ffmpeg-deps \
    && cd /app/ffmpeg-deps \
    && ldd /usr/bin/ffmpeg | grep '=> /' \
    | awk '{print $3}' \
    | grep -v 'ld-musl-x86_64.so.1' \
    | xargs -I '{}' cp -v '{}' .

FROM python:3.12-alpine

# Copy over ffmpeg and its dependencies
COPY --from=builder /usr/bin/ffmpeg /usr/bin/ffmpeg
COPY --from=builder /usr/bin/ffprobe /usr/bin/ffprobe
COPY --from=builder /app/ffmpeg-deps/lib* /usr/lib/

# Copy the wheel file from the builder stage
COPY --from=builder /app/wheels/*.whl .

# Install the wheel file
RUN pip install --no-deps *.whl

# Clean up installation
RUN rm *.whl

ENTRYPOINT ["zyspotify"]
