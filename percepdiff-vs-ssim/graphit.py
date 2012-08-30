import json
import matplotlib.pyplot as plt
from matplotlib import rc

rc('text', usetex=True)
rc('font', family='sans-serif')
rc('font', size='18')

pyssim = json.loads(open('pyssim.json', 'r').read())
percepdiff = json.loads(open('perceptualdiff.json', 'r').read())

x_vals = [float('.'.join(d['filename'].split('.')[:-1])) for d in pyssim]
ssim_y = [1.0 - d['comparison_val'] for d in pyssim]
percepdiff_y = [d['perceptualdiff'] / float(1024*768) for d in percepdiff]
ratio = [v1 / float(v2) for v1, v2 in zip(ssim_y, percepdiff_y)]

fig = plt.figure(figsize=(11.5,8))

ax1 = fig.add_subplot(111)
p1 = ax1.plot(x_vals, ssim_y, marker='p', color='blue')
p2 = ax1.plot(x_vals, percepdiff_y, marker='s', color='red')
plt.ylim((0, 0.8))
plt.xlabel('Time (s)')
plt.ylabel('Normalized SSIM and perceputaldiff')

ax2 = ax1.twinx()
p3 = ax2.plot(x_vals, ratio, marker='*', color='green')
plt.ylabel('SSIM / perceptualdiff')

plt.legend(p1+p2+p3, ['SSIM', 'peceptualdiff', 'Ratio'])

plt.subplots_adjust(left=0.08, right=0.91, top=0.94, bottom=0.1)
plt.title('Perceptualdiff vs. SSIM')
plt.savefig('percepdiff-vs-pyssim.pdf')

