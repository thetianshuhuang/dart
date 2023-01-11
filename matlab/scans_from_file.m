% function scans = scans_from_file(filename)

load(filename, 'frames', 'start_time', 'end_time');
N = size(frames, 1);
dt_start = datetime(start_time, 'InputFormat', 'yyyy-MM-dd''T''HH:mm:ss.SSSSSS''Z''');
dt_end = datetime(end_time, 'InputFormat', 'yyyy-MM-dd''T''HH:mm:ss.SSSSSS''Z''');

chirplen = 512;
framelen = 1024;
a = squeeze(frames(:,1,1,:));
a = a(1:(floor(size(a, 1) / framelen)*framelen), :);
b = reshape(a.', chirplen, framelen, []);

for i = 1:126
    c = fftshift(fft2(b(:,:,i)));
    imagesc(abs(c));
    pause(0.2);
end

% end
