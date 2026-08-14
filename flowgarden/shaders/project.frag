#version 430 core

in vec2 v_uv;
layout(location = 0) out vec2 out_velocity;
layout(binding = 0) uniform sampler2D u_velocity;
layout(binding = 1) uniform sampler2D u_pressure;

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_velocity, 0));
    float left = texture(u_pressure, v_uv - vec2(texel.x, 0.0)).r;
    float right = texture(u_pressure, v_uv + vec2(texel.x, 0.0)).r;
    float bottom = texture(u_pressure, v_uv - vec2(0.0, texel.y)).r;
    float top = texture(u_pressure, v_uv + vec2(0.0, texel.y)).r;
    vec2 velocity = texture(u_velocity, v_uv).xy - 0.5 * vec2(right - left, top - bottom);

    if (v_uv.x < texel.x * 2.0 || v_uv.x > 1.0 - texel.x * 2.0) velocity.x = 0.0;
    if (v_uv.y < texel.y * 2.0 || v_uv.y > 1.0 - texel.y * 2.0) velocity.y = 0.0;
    out_velocity = velocity;
}
