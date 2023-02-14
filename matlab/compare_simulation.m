close all;

datadir = 'D:\dartdata';
dataset = 'cubes';

real_rad = rad;
load(simfile, 'rad');
sim_rad = rad;
rad = real_rad;

x = linspace(min_doppler, max_doppler, res_doppler);
y = linspace(min_range, max_range/2, floor(res_range/2));

fig = figure;
subplot(2,3,[2,3,5,6]);
facing = zeros(size(pos));
for i = 1:size(facing, 1)
    r = squeeze(rot(i, :, :));
    facing(i, :) = (r * [1; 0; 0]).';
end
quiver3(pos(:,1),pos(:,2),pos(:,3),facing(:,1),facing(:,2),facing(:,3));
hold on
v = max(min(vel,0.2),-0.2);
quiver3(pos(:,1),pos(:,2),pos(:,3),v(:,1),v(:,2),v(:,3));
[fo, vo] = isosurface(map.x,map.y,map.z,map.v);
patch('Faces',fo,'Vertices',vo,'FaceColor','#909090','EdgeColor','None');
axis equal; axis vis3d;

N = size(rad, 1);
sld = uicontrol('Parent',fig,'Style','slider','Value',1,'min',1,'max',N,'Position',[1200,125,1200,50],'SliderStep',[1,1]./(N-1));
bl1 = uicontrol('Parent',fig,'Style','text','Position',[1150,135,23,30],'String','0','FontSize',16);
tend = string(t(end)-t(1));
bl2 = uicontrol('Parent',fig,'Style','text','Position',[2420,135,100,30],'String',tend,'FontSize',16);
bl3 = uicontrol('Parent',fig,'Style','text','Position',[1750,90,100,30],'String','Time (s)','FontSize',16);

ts = t(2)-t(1);
while true
    sld.Value = round(sld.Value);
    c = squeeze(real_rad(sld.Value,1:64,:));
    d = squeeze(sim_rad(sld.Value,1:64,:));
    c(:,33) = 0;
    d(:,33) = 0;
    subplot(2,3,1);
    imcomplex(x, y, c);
    subplot(2,3,4);
    imcomplex(x, y, d);
    pause(ts);
end
