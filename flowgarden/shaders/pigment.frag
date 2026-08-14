#version 430 core

in vec2 v_uv;
layout(location = 0) out vec4 out_pigment;
layout(binding = 0) uniform sampler2D u_pigment;
layout(binding = 1) uniform sampler2D u_velocity;

uniform float u_dt;

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_pigment, 0));
    vec2 velocity = texture(u_velocity, v_uv).xy;
    vec2 back = clamp(v_uv - velocity * u_dt, texel, 1.0 - texel);
    vec4 pigment = max(texture(u_pigment, back), vec4(0.00001));

    // A small sharpening step preserves distinct artistic pigment regions.
    pigment = pow(pigment, vec4(1.035));
    pigment /= dot(pigment, vec4(1.0));
    out_pigment = pigment;
}
