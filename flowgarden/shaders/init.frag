#version 410 core

in vec2 v_uv;
layout(location = 0) out vec4 out_pigment;

uniform float u_seed;
uniform float u_aspect;

float basin(vec2 p, vec2 center, vec2 satellite, vec2 direction, float phase) {
    float primary = -8.0 * dot(p - center, p - center);
    float island = -10.0 * dot(p - satellite, p - satellite) - 0.75;
    float contour = 0.28 * sin(dot(p, direction) * 7.0 + phase);
    return max(primary, island) + contour;
}

void main() {
    float seed = u_seed * 0.071;
    vec2 p = (v_uv - 0.5) * vec2(u_aspect, 1.0);
    p += 0.045 * vec2(
        sin(p.y * 9.0 + seed) + sin((p.x + p.y) * 5.0 - seed * 0.7),
        cos(p.x * 8.0 - seed) + cos((p.x - p.y) * 6.0 + seed * 0.6)
    );

    float x = 0.23 * u_aspect;
    vec2 jitter = 0.035 * vec2(sin(seed * 1.7), cos(seed * 1.3));
    vec4 f = vec4(
        basin(p, vec2(-x, -0.22) + jitter, vec2(x * 1.45, 0.03), vec2(0.8, 0.5), seed),
        basin(p, vec2(x, -0.20) - jitter, vec2(-x * 1.5, 0.12), vec2(-0.4, 0.9), seed + 1.7),
        basin(p, vec2(-x, 0.22) - jitter.yx, vec2(x * 1.55, -0.05), vec2(0.6, -0.8), seed + 3.4),
        basin(p, vec2(x, 0.21) + jitter.yx, vec2(-x * 1.4, -0.13), vec2(-0.9, -0.3), seed + 5.1)
    );
    f = exp((f - max(max(f.x, f.y), max(f.z, f.w))) * 4.2);
    out_pigment = f / dot(f, vec4(1.0));
}
