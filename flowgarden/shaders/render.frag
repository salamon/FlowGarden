#version 430 core

in vec2 v_uv;
layout(location = 0) out vec4 out_color;
layout(binding = 0) uniform sampler2D u_pigment;
layout(binding = 1) uniform sampler2D u_velocity;

uniform float u_time;
uniform float u_aspect;
uniform int u_auto;
uniform vec2 u_mouse;
uniform float u_brush;
uniform int u_mouse_kind;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    vec4 w = max(texture(u_pigment, v_uv), vec4(0.0));
    vec4 crisp = pow(w, vec4(7.0));
    crisp /= max(dot(crisp, vec4(1.0)), 0.0001);

    const vec3 jade = vec3(0.075, 0.63, 0.57);
    const vec3 coral = vec3(0.95, 0.27, 0.31);
    const vec3 amber = vec3(0.96, 0.65, 0.12);
    const vec3 violet = vec3(0.43, 0.26, 0.76);
    vec3 color = jade * crisp.x + coral * crisp.y + amber * crisp.z + violet * crisp.w;

    float strongest = max(max(w.x, w.y), max(w.z, w.w));
    vec4 remaining = w;
    if (strongest == w.x) remaining.x = 0.0;
    else if (strongest == w.y) remaining.y = 0.0;
    else if (strongest == w.z) remaining.z = 0.0;
    else remaining.w = 0.0;
    float second = max(max(remaining.x, remaining.y), max(remaining.z, remaining.w));
    float boundary = 1.0 - smoothstep(0.015, 0.22, strongest - second);

    vec2 velocity = texture(u_velocity, v_uv).xy;
    float speed = min(1.0, length(velocity) * 2.8);
    float grain = hash21(gl_FragCoord.xy + floor(u_time * 3.0)) - 0.5;
    float rake = sin((strongest + v_uv.x * 0.07 - v_uv.y * 0.04) * 115.0);
    rake = smoothstep(0.82, 1.0, rake) * (1.0 - boundary) * 0.035;

    color *= 0.84 + strongest * 0.25;
    color += speed * 0.08 + rake + grain * 0.018;
    color *= 1.0 - boundary * 0.23;
    color += boundary * vec3(0.75, 0.88, 0.84) * 0.09;

    float vignette = 1.0 - 0.28 * dot(v_uv - 0.5, v_uv - 0.5);
    color *= vignette;

    if (u_auto == 0 && u_mouse_kind == 1) {
        vec2 d = v_uv - u_mouse;
        d.x *= u_aspect;
        float ring = abs(length(d) - u_brush);
        color += vec3(0.85, 0.95, 0.90) * (1.0 - smoothstep(0.001, 0.0035, ring)) * 0.5;
    }

    color = pow(max(color, vec3(0.0)), vec3(0.92));
    out_color = vec4(color, 1.0);
}
