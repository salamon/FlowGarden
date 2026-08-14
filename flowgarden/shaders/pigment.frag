#version 410 core

in vec2 v_uv;
layout(location = 0) out vec4 out_pigment;
uniform sampler2D u_pigment;
uniform sampler2D u_velocity;

uniform float u_dt;
uniform float u_aspect;

const int MAX_ROCKS = 8;
uniform int u_rock_count;
uniform vec4 u_rocks[MAX_ROCKS];
uniform vec2 u_rock_meta[MAX_ROCKS];

vec2 rotate_point(vec2 point, float angle) {
    float cosine = cos(angle);
    float sine = sin(angle);
    return vec2(cosine * point.x - sine * point.y, sine * point.x + cosine * point.y);
}

float rock_distance(vec2 uv, int index) {
    vec4 rock = u_rocks[index];
    float angle = u_rock_meta[index].x;
    float shape = u_rock_meta[index].y;
    vec2 point = vec2((uv.x - rock.x) * u_aspect, uv.y - rock.y);
    vec2 local = rotate_point(point, -angle);
    float theta = atan(local.y, local.x);
    float irregularity = 1.0 + 0.065 * sin(theta * 3.0 + shape * 6.2832)
        + 0.035 * sin(theta * 5.0 - shape * 4.7124);
    return length(local / (rock.zw * irregularity)) - 1.0;
}

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_pigment, 0));
    vec2 velocity = texture(u_velocity, v_uv).xy;
    vec2 back = clamp(v_uv - velocity * u_dt, texel, 1.0 - texel);
    bool blocked = false;
    for (int i = 0; i < u_rock_count; ++i) {
        blocked = blocked || rock_distance(back, i) < 0.0;
    }
    vec4 pigment = max(texture(u_pigment, blocked ? v_uv : back), vec4(0.00001));

    // A small sharpening step preserves distinct artistic pigment regions.
    pigment = pow(pigment, vec4(1.035));
    pigment /= dot(pigment, vec4(1.0));
    out_pigment = pigment;
}
