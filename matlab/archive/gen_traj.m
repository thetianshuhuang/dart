function [traj, t_sample] = gen_traj()

T = 10;
fs = 1000;
waypoints = [ ...
    -12, -12, -5; ...
    -10, 10, -3.75; ...
    8, 8, -2.5; ...
    6, -6, -1.25; ...
    -4, -4, 0; ...
    -6, 6, 1.25; ...
    8, 8, 2.5; ...
    10, -10, 3.75; ...
    -12, -12, 5; ...
]*0.5;
dirs = cat(3, ...
    axang2rotm([0, 0, 1, deg2rad(45)]), ...
    axang2rotm([0, 0, 1, deg2rad(-45)]), ...
    axang2rotm([0, 0, 1, deg2rad(-135)]), ...
    axang2rotm([0, 0, 1, deg2rad(-225)]), ...
    axang2rotm([0, 0, 1, deg2rad(-315)]), ...
    axang2rotm([0, 0, 1, deg2rad(-45)]), ...
    axang2rotm([0, 0, 1, deg2rad(-135)]), ...
    axang2rotm([0, 0, 1, deg2rad(-225)]), ...
    axang2rotm([0, 0, 1, deg2rad(-315)]) ...
);

waypoint_ts = linspace(0, T, size(waypoints, 1)).';
traj = waypointTrajectory(waypoints, waypoint_ts, Orientation=dirs, ReferenceFrame='ENU');

t_sample = [0 : 1/fs : T-1/fs].';

end