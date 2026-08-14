#version 410 core

in vec2 v_uv;
layout(location = 0) out vec4 out_color;
uniform sampler2D u_pigment;
uniform sampler2D u_velocity;

uniform float u_time;
uniform float u_aspect;
uniform int u_auto;
uniform vec2 u_mouse;
uniform float u_brush;
uniform int u_mouse_kind;
uniform int u_palette;

const int MAX_ROCKS = 8;
uniform int u_rock_count;
uniform vec4 u_rocks[MAX_ROCKS];
uniform vec2 u_rock_meta[MAX_ROCKS];

vec2 rotate_point(vec2 point, float angle) {
    float cosine = cos(angle);
    float sine = sin(angle);
    return vec2(cosine * point.x - sine * point.y, sine * point.x + cosine * point.y);
}

float rock_distance(vec2 uv, int index, out vec2 local) {
    vec4 rock = u_rocks[index];
    float angle = u_rock_meta[index].x;
    float shape = u_rock_meta[index].y;
    vec2 point = vec2((uv.x - rock.x) * u_aspect, uv.y - rock.y);
    local = rotate_point(point, -angle);
    float theta = atan(local.y, local.x);
    float irregularity = 1.0 + 0.065 * sin(theta * 3.0 + shape * 6.2832)
        + 0.035 * sin(theta * 5.0 - shape * 4.7124);
    return length(local / (rock.zw * irregularity)) - 1.0;
}

mat4 color_palette(int palette) {
    if (palette == 1) {
        return mat4(
            vec4(0.04, 0.20, 0.48, 1.0),
            vec4(0.06, 0.68, 0.78, 1.0),
            vec4(0.34, 0.82, 0.68, 1.0),
            vec4(0.94, 0.72, 0.38, 1.0)
        );
    }
    if (palette == 2) {
        return mat4(
            vec4(0.14, 0.08, 0.12, 1.0),
            vec4(0.72, 0.08, 0.16, 1.0),
            vec4(0.96, 0.31, 0.08, 1.0),
            vec4(1.00, 0.75, 0.18, 1.0)
        );
    }
    if (palette == 3) {
        return mat4(
            vec4(0.24, 0.16, 0.46, 1.0),
            vec4(0.73, 0.18, 0.50, 1.0),
            vec4(0.96, 0.45, 0.62, 1.0),
            vec4(1.00, 0.78, 0.72, 1.0)
        );
    }
    if (palette == 4) {
        return mat4(
            vec4(0.05, 0.28, 0.26, 1.0),
            vec4(0.10, 0.62, 0.55, 1.0),
            vec4(0.78, 0.50, 0.10, 1.0),
            vec4(0.62, 0.20, 0.15, 1.0)
        );
    }
    return mat4(
        vec4(0.075, 0.63, 0.57, 1.0),
        vec4(0.95, 0.27, 0.31, 1.0),
        vec4(0.96, 0.65, 0.12, 1.0),
        vec4(0.43, 0.26, 0.76, 1.0)
    );
}

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    vec4 w = max(texture(u_pigment, v_uv), vec4(0.0));
    vec4 crisp = pow(w, vec4(7.0));
    crisp /= max(dot(crisp, vec4(1.0)), 0.0001);

    mat4 palette = color_palette(u_palette);
    vec3 color =
        palette[0].rgb * crisp.x +
        palette[1].rgb * crisp.y +
        palette[2].rgb * crisp.z +
        palette[3].rgb * crisp.w;

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

    float closest_rock = 1000.0;
    float closest_shadow = 1000.0;
    vec2 closest_local = vec2(0.0);
    vec2 shadow_local;
    int closest_index = 0;
    for (int i = 0; i < u_rock_count; ++i) {
        vec2 local;
        float distance_to_rock = rock_distance(v_uv, i, local);
        if (distance_to_rock < closest_rock) {
            closest_rock = distance_to_rock;
            closest_local = local;
            closest_index = i;
        }
        float shadow_distance = rock_distance(v_uv - vec2(0.008 / u_aspect, -0.012), i, shadow_local);
        closest_shadow = min(closest_shadow, shadow_distance);
    }

    float rock_mask = 1.0 - smoothstep(-0.015, 0.018, closest_rock);
    float shadow_mask = (1.0 - smoothstep(-0.02, 0.22, closest_shadow)) * (1.0 - rock_mask);
    color *= 1.0 - shadow_mask * 0.34;

    if (rock_mask > 0.0) {
        vec2 scaled = closest_local / u_rocks[closest_index].zw;
        vec3 normal = normalize(vec3(-scaled.x * 0.55, scaled.y * 0.55, 1.0));
        float lighting = 0.48 + 0.52 * max(0.0, dot(normal, normalize(vec3(-0.45, 0.65, 0.85))));
        float stone_grain = hash21(gl_FragCoord.xy * 0.35 + u_rock_meta[closest_index].yy * 91.0) - 0.5;
        float edge = 1.0 - smoothstep(0.0, 0.11, abs(closest_rock));
        vec3 stone = mix(vec3(0.16, 0.17, 0.17), vec3(0.46, 0.48, 0.46), lighting);
        stone += stone_grain * 0.055;
        stone *= 1.0 - edge * 0.16;
        color = mix(color, stone, rock_mask);
    }

    if (u_auto == 0 && u_mouse_kind == 1) {
        vec2 d = v_uv - u_mouse;
        d.x *= u_aspect;
        float ring = abs(length(d) - u_brush);
        color += vec3(0.85, 0.95, 0.90) * (1.0 - smoothstep(0.001, 0.0035, ring)) * 0.5;
    }

    color = pow(max(color, vec3(0.0)), vec3(0.92));
    out_color = vec4(color, 1.0);
}
