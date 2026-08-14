#version 410 core

in vec2 v_uv;
layout(location = 0) out vec2 out_velocity;
uniform sampler2D u_velocity;
uniform sampler2D u_pressure;

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

float rock_distance(vec2 uv, int index, out vec2 normal) {
    vec4 rock = u_rocks[index];
    float angle = u_rock_meta[index].x;
    float shape = u_rock_meta[index].y;
    vec2 point = vec2((uv.x - rock.x) * u_aspect, uv.y - rock.y);
    vec2 local = rotate_point(point, -angle);
    float theta = atan(local.y, local.x);
    float irregularity = 1.0 + 0.065 * sin(theta * 3.0 + shape * 6.2832)
        + 0.035 * sin(theta * 5.0 - shape * 4.7124);
    vec2 radii = rock.zw * irregularity;
    vec2 scaled = local / radii;
    vec2 local_normal = normalize(vec2(local.x / (radii.x * radii.x), local.y / (radii.y * radii.y)));
    normal = rotate_point(local_normal, angle);
    return length(scaled) - 1.0;
}

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_velocity, 0));
    float left = texture(u_pressure, v_uv - vec2(texel.x, 0.0)).r;
    float right = texture(u_pressure, v_uv + vec2(texel.x, 0.0)).r;
    float bottom = texture(u_pressure, v_uv - vec2(0.0, texel.y)).r;
    float top = texture(u_pressure, v_uv + vec2(0.0, texel.y)).r;
    vec2 velocity = texture(u_velocity, v_uv).xy - 0.5 * vec2(right - left, top - bottom);

    vec2 physical_velocity = velocity * vec2(u_aspect, 1.0);
    for (int i = 0; i < u_rock_count; ++i) {
        vec2 normal;
        float distance_to_rock = rock_distance(v_uv, i, normal);
        if (distance_to_rock < 0.0) {
            physical_velocity = vec2(0.0);
        } else if (distance_to_rock < 0.18) {
            float inward_speed = dot(physical_velocity, normal);
            if (inward_speed < 0.0) {
                float proximity = 1.0 - smoothstep(0.0, 0.18, distance_to_rock);
                physical_velocity -= normal * inward_speed * (1.0 + 0.55 * proximity);
            }
        }
    }
    velocity = physical_velocity / vec2(u_aspect, 1.0);

    if (v_uv.x < texel.x * 2.0 || v_uv.x > 1.0 - texel.x * 2.0) velocity.x = 0.0;
    if (v_uv.y < texel.y * 2.0 || v_uv.y > 1.0 - texel.y * 2.0) velocity.y = 0.0;
    out_velocity = velocity;
}
