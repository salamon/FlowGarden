#version 430 core

in vec2 v_uv;
layout(location = 0) out float out_pressure;
layout(binding = 0) uniform sampler2D u_pressure;
layout(binding = 1) uniform sampler2D u_divergence;

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_pressure, 0));
    float left = texture(u_pressure, v_uv - vec2(texel.x, 0.0)).r;
    float right = texture(u_pressure, v_uv + vec2(texel.x, 0.0)).r;
    float bottom = texture(u_pressure, v_uv - vec2(0.0, texel.y)).r;
    float top = texture(u_pressure, v_uv + vec2(0.0, texel.y)).r;
    float divergence = texture(u_divergence, v_uv).r;
    out_pressure = (left + right + bottom + top - divergence) * 0.25;
}
