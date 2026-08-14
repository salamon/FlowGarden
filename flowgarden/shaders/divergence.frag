#version 410 core

in vec2 v_uv;
layout(location = 0) out float out_divergence;
uniform sampler2D u_velocity;

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_velocity, 0));
    float left = texture(u_velocity, v_uv - vec2(texel.x, 0.0)).x;
    float right = texture(u_velocity, v_uv + vec2(texel.x, 0.0)).x;
    float bottom = texture(u_velocity, v_uv - vec2(0.0, texel.y)).y;
    float top = texture(u_velocity, v_uv + vec2(0.0, texel.y)).y;
    out_divergence = 0.5 * ((right - left) + (top - bottom));
}
