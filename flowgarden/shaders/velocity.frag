#version 430 core

in vec2 v_uv;
layout(location = 0) out vec2 out_velocity;
layout(binding = 0) uniform sampler2D u_velocity;

uniform float u_dt;
uniform float u_time;
uniform float u_aspect;
uniform float u_seed;
uniform int u_auto;
uniform vec2 u_mouse;
uniform vec2 u_mouse_delta;
uniform int u_mouse_kind;
uniform float u_brush;

vec2 flow_field(vec2 p, float t) {
    float seed = u_seed * 0.017;
    vec2 q = p * vec2(u_aspect, 1.0);
    vec2 f = vec2(
        sin(q.y * 7.0 + t * 0.37 + seed) + 0.55 * cos((q.x + q.y) * 11.0 - t * 0.21),
        cos(q.x * 6.0 - t * 0.31 - seed) - 0.55 * sin((q.x - q.y) * 10.0 + t * 0.27)
    );

    vec2 center = vec2(
        0.5 + 0.24 * sin(t * 0.13 + seed),
        0.5 + 0.20 * cos(t * 0.17 - seed)
    );
    vec2 d = p - center;
    d.x *= u_aspect;
    f += vec2(-d.y, d.x) * exp(-dot(d, d) * 4.0) * 2.2;
    return f;
}

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_velocity, 0));
    vec2 previous = texture(u_velocity, v_uv).xy;
    vec2 back = clamp(v_uv - previous * u_dt, texel, 1.0 - texel);
    vec2 velocity = texture(u_velocity, back).xy;

    vec2 neighbors =
        texture(u_velocity, back + vec2(texel.x, 0.0)).xy +
        texture(u_velocity, back - vec2(texel.x, 0.0)).xy +
        texture(u_velocity, back + vec2(0.0, texel.y)).xy +
        texture(u_velocity, back - vec2(0.0, texel.y)).xy;
    velocity = mix(velocity, neighbors * 0.25, min(0.12, u_dt * 4.0));

    if (u_auto == 1) {
        velocity += flow_field(v_uv, u_time) * u_dt * 0.055;
        velocity *= exp(-u_dt * 0.34);
    } else {
        velocity *= exp(-u_dt * 8.0);
    }

    if (u_mouse_kind != 0) {
        vec2 d = v_uv - u_mouse;
        d.x *= u_aspect;
        float influence = exp(-dot(d, d) / max(0.0001, u_brush * u_brush) * 3.0);
        if (u_mouse_kind > 0) {
            velocity += u_mouse_delta * influence * 22.0;
        } else {
            vec2 tangent = normalize(vec2(-d.y, d.x) + vec2(0.0001));
            float gesture = 0.14 + min(0.6, length(u_mouse_delta) * 12.0);
            velocity += tangent * influence * gesture;
        }
    }

    vec2 wall = smoothstep(vec2(0.0), texel * 3.0, v_uv) *
                smoothstep(vec2(0.0), texel * 3.0, 1.0 - v_uv);
    out_velocity = clamp(velocity * wall.x * wall.y, vec2(-1.2), vec2(1.2));
}
