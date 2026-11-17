/*
 * mtkaudio: carica l'HAL audio MediaTek di MIUI (audio.primary.mt6765.so) con libhardware
 * e lo comanda da una piccola shell su stdin, senza audioserver né binder.
 * Gira dentro il contenitore (bionic a 32 bit, linker /system/bin/linker).
 *
 * Comandi (uno per riga):
 *   mode <n>            set_mode: 0 normale, 2 in chiamata, 3 VoIP
 *   param <k=v;...>     set_parameters del dispositivo
 *   get <chiavi>        get_parameters del dispositivo
 *   vol <0..1>          set_voice_volume
 *   mute <0|1>          set_mic_mute
 *   open <dev> <flags> <rate> [canali]   apre lo stream di uscita (dev e flags in esadecimale)
 *   oparam <k=v;...>    set_parameters dello stream di uscita
 *   play <file.raw>     scrive PCM 16 bit sullo stream di uscita
 *   close               chiude lo stream di uscita
 *   mopen <rate> [canali]  apre lo stream "incall music" (flag 0x10000 verso 0x10000, la rete): MediaTek
 *                       lo manda al modem come background sound, lo sente chi è in linea
 *   mplay <file.raw>    scrive PCM 16 bit sullo stream incall music
 *   mclose              chiude lo stream incall music
 *   iopen <dev> <sorgente> <rate> [canali]  apre lo stream di ingresso (dev in esadecimale); per la voce
 *                       di chi chiama: 80000040 (rete) con sorgente 3 (downlink) o 4 (chiamata)
 *   rec <file.raw> <s>  registra PCM 16 bit dallo stream di ingresso per <s> secondi
 *   recvad <file.raw> <max_s> [silenzio_ms] [soglia]  registra finché chi parla tace: parte al primo frame
 *                       sopra soglia (RMS), si ferma dopo silenzio_ms sotto soglia o dopo max_s; stampa
 *                       "recvad: <byte> parlato <0|1>"
 *   iclose              chiude lo stream di ingresso
 *   patch <src> <sink>  create_audio_patch da dispositivo a dispositivo (tipi in esadecimale), come fa
 *                       Android 10 in chiamata: 80000040 (rete) -> 2 (altoparlante), 80000004 (microfono) -> 10000 (rete)
 *   mixpatch <sink>     create_audio_patch dallo stream di uscita aperto (handle 13) a un dispositivo
 *   unpatch <handle>    release_audio_patch
 *   unpatchall          rilascia tutte le patch create
 *   sleep <s>
 *   quit
 * Costruzione: vedi build.sh
 */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef long ssize_t;
typedef struct FILE FILE;
extern FILE *stdin, *stdout;
int printf(const char *, ...);
int fflush(FILE *);
char *fgets(char *, int, FILE *);
int strncmp(const char *, const char *, size_t);
size_t strlen(const char *);
unsigned long strtoul(const char *, char **, int);
double strtod(const char *, char **);
int open(const char *, int, ...);
ssize_t read(int, void *, size_t);
ssize_t write(int, const void *, size_t);
int close(int);
unsigned int sleep(unsigned int);
int usleep(unsigned int);
void free(void *);
int setvbuf(FILE *, char *, int, size_t);

/* ---- libhardware (Android 10, 32 bit) ---- */
struct hw_module_t;
struct hw_device_t;
struct hw_module_methods_t {
	int (*open)(const struct hw_module_t *, const char *, struct hw_device_t **);
};
struct hw_module_t {
	uint32_t tag;
	uint16_t module_api_version, hal_api_version;
	const char *id, *name, *author;
	struct hw_module_methods_t *methods;
	void *dso;
	uint32_t reserved[32 - 7];
};
struct hw_device_t {
	uint32_t tag, version;
	struct hw_module_t *module;
	uint32_t reserved[12];
	int (*close)(struct hw_device_t *);
};
int hw_get_module_by_class(const char *, const char *, const struct hw_module_t **);

/* ---- audio.h ---- */
typedef struct {
	uint16_t version, size;
	uint32_t sample_rate, channel_mask, format, stream_type, bit_rate;
	int64_t duration_us;
	bool has_video, is_streaming;
	uint32_t bit_width, offload_buffer_size, usage;
} __attribute__((aligned(8))) audio_offload_info_t;
struct audio_config {
	uint32_t sample_rate, channel_mask, format;
	audio_offload_info_t offload_info;
	uint32_t frame_count;
};
struct audio_stream {
	uint32_t (*get_sample_rate)(const struct audio_stream *);
	int (*set_sample_rate)(struct audio_stream *, uint32_t);
	size_t (*get_buffer_size)(const struct audio_stream *);
	uint32_t (*get_channels)(const struct audio_stream *);
	uint32_t (*get_format)(const struct audio_stream *);
	int (*set_format)(struct audio_stream *, uint32_t);
	int (*standby)(struct audio_stream *);
	int (*dump)(const struct audio_stream *, int);
	uint32_t (*get_device)(const struct audio_stream *);
	int (*set_device)(struct audio_stream *, uint32_t);
	int (*set_parameters)(struct audio_stream *, const char *);
	char *(*get_parameters)(const struct audio_stream *, const char *);
	int (*add_audio_effect)(const struct audio_stream *, void *);
	int (*remove_audio_effect)(const struct audio_stream *, void *);
};
struct audio_stream_out {
	struct audio_stream common;
	uint32_t (*get_latency)(const struct audio_stream_out *);
	int (*set_volume)(struct audio_stream_out *, float, float);
	ssize_t (*write)(struct audio_stream_out *, const void *, size_t);
};
struct audio_stream_in {
	struct audio_stream common;
	int (*set_gain)(struct audio_stream_in *, float);
	ssize_t (*read)(struct audio_stream_in *, void *, size_t);
};
struct audio_gain_config {
	int index;
	uint32_t mode, channel_mask;
	int values[32];
	unsigned int ramp_duration_ms;
};
struct audio_port_config {
	int id;
	uint32_t role, type; /* ruolo: 1 sorgente, 2 destinazione; tipo: 1 dispositivo, 2 mix */
	unsigned int config_mask;
	unsigned int sample_rate;
	uint32_t channel_mask, format;
	struct audio_gain_config gain;
	uint32_t flags;
	union {
		struct { int hw_module; uint32_t type; char address[32]; } device;
		struct { int hw_module; int handle; int usecase; } mix;
		struct { int session; } session;
	} ext;
};
struct audio_hw_device {
	struct hw_device_t common;
	uint32_t (*get_supported_devices)(const struct audio_hw_device *);
	int (*init_check)(const struct audio_hw_device *);
	int (*set_voice_volume)(struct audio_hw_device *, float);
	int (*set_master_volume)(struct audio_hw_device *, float);
	int (*get_master_volume)(struct audio_hw_device *, float *);
	int (*set_mode)(struct audio_hw_device *, int);
	int (*set_mic_mute)(struct audio_hw_device *, bool);
	int (*get_mic_mute)(const struct audio_hw_device *, bool *);
	int (*set_parameters)(struct audio_hw_device *, const char *);
	char *(*get_parameters)(const struct audio_hw_device *, const char *);
	size_t (*get_input_buffer_size)(const struct audio_hw_device *, const struct audio_config *);
	int (*open_output_stream)(struct audio_hw_device *, int handle, uint32_t devices,
				  uint32_t flags, struct audio_config *, struct audio_stream_out **,
				  const char *address);
	void (*close_output_stream)(struct audio_hw_device *, struct audio_stream_out *);
	int (*open_input_stream)(struct audio_hw_device *, int, uint32_t, struct audio_config *,
				 struct audio_stream_in **, uint32_t flags, const char *address, uint32_t source);
	void (*close_input_stream)(struct audio_hw_device *, struct audio_stream_in *);
	int (*get_microphones)(const struct audio_hw_device *, void *, size_t *);
	int (*dump)(const struct audio_hw_device *, int);
	int (*set_master_mute)(struct audio_hw_device *, bool);
	int (*get_master_mute)(struct audio_hw_device *, bool *);
	int (*create_audio_patch)(struct audio_hw_device *, unsigned int, const struct audio_port_config *,
				  unsigned int, const struct audio_port_config *, int *handle);
	int (*release_audio_patch)(struct audio_hw_device *, int handle);
};

static void port_device(struct audio_port_config *p, uint32_t role, uint32_t type)
{
	p->id = 0;
	p->role = role;
	p->type = 1; /* AUDIO_PORT_TYPE_DEVICE */
	p->config_mask = 0;
	p->ext.device.hw_module = 10; /* handle del modulo primario, come in audioserver */
	p->ext.device.type = type;
}

/* ---- avvio senza crtbegin: bionic __libc_init ---- */
struct structors { void (**preinit)(void); void (**init)(void); void (**fini)(void); };
static const struct structors no_structors = { 0, 0, 0 };
__attribute__((noreturn)) void __libc_init(void *, void (*)(void), int (*)(int, char **, char **),
					   const struct structors *);
int main(int, char **, char **);
__attribute__((used, noreturn)) void start_c(void *sp)
{
	__libc_init(sp, 0, main, &no_structors);
}
__attribute__((naked, noreturn)) void _start(void)
{
	__asm__ volatile("mov r0, sp\n\tb start_c\n");
}

/* ---- shell ---- */
static struct audio_hw_device *dev;
static struct audio_stream_out *out, *music;
static struct audio_stream_in *in;
static int patches[16], npatches;

static void keep_patch(int r, int h)
{
	if (!r && npatches < 16) patches[npatches++] = h;
}

static struct audio_stream_out *open_out(int handle, uint32_t d, uint32_t f, uint32_t rate, uint32_t ch)
{
	struct audio_stream_out *o = 0;
	struct audio_config c = { 0 };
	c.sample_rate = rate ? rate : 48000;
	c.channel_mask = ch == 1 ? 0x1 : 0x3; /* MONO / STEREO */
	c.format = 0x1; /* PCM_16_BIT */
	c.offload_info.version = 0x0201;
	c.offload_info.size = sizeof c.offload_info;
	int r = dev->open_output_stream(dev, handle, d, f, &c, &o, "");
	printf("open_output_stream(%x, %x): %d rate %u ch %x fmt %x\n", d, f, r, c.sample_rate,
	       c.channel_mask, c.format);
	if (r) return 0;
	printf("buffer %u byte, latenza %u ms\n", (unsigned)o->common.get_buffer_size(&o->common),
	       o->get_latency(o));
	return o;
}

static void play(struct audio_stream_out *o, const char *path)
{
	static char buf[16384];
	ssize_t k, tot = 0;
	int fd = open(path, 0);
	if (fd < 0 || !o) { printf("play: errore\n"); if (fd >= 0) close(fd); return; }
	size_t bs = o->common.get_buffer_size(&o->common);
	if (bs > sizeof buf) bs = sizeof buf;
	while ((k = read(fd, buf, bs)) > 0) {
		ssize_t w = o->write(o, buf, k);
		if (w < 0) { printf("write: %d\n", (int)w); break; }
		tot += w;
	}
	close(fd);
	printf("play: %d byte\n", (int)tot);
}

static char *arg(char *s)
{
	while (*s && *s != ' ') s++;
	while (*s == ' ') s++;
	return s;
}

int main(int argc, char **argv, char **envp)
{
	const struct hw_module_t *mod;
	char line[1024];
	int r;

	setvbuf(stdout, 0, 2 /* _IONBF */, 0);
	r = hw_get_module_by_class("audio", "primary", &mod);
	printf("hw_get_module: %d\n", r);
	if (r) return 1;
	printf("modulo: %s (%s) api %x\n", mod->name, mod->author, mod->module_api_version);
	r = mod->methods->open(mod, "audio_hw_if", (struct hw_device_t **)&dev);
	printf("open: %d versione %x\n", r, r ? 0 : dev->common.version);
	if (r) return 1;
	printf("init_check: %d\n", dev->init_check(dev));
	printf("pronto\n");

	while (fgets(line, sizeof line, stdin)) {
		size_t n = strlen(line);
		while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = 0;
		char *a = arg(line);
		if (!strncmp(line, "mode ", 5)) {
			printf("set_mode: %d\n", dev->set_mode(dev, (int)strtoul(a, 0, 0)));
		} else if (!strncmp(line, "param ", 6)) {
			printf("set_parameters: %d\n", dev->set_parameters(dev, a));
		} else if (!strncmp(line, "get ", 4)) {
			char *v = dev->get_parameters(dev, a);
			printf("get_parameters: %s\n", v ? v : "(null)");
			free(v);
		} else if (!strncmp(line, "vol ", 4)) {
			printf("set_voice_volume: %d\n", dev->set_voice_volume(dev, (float)strtod(a, 0)));
		} else if (!strncmp(line, "mute ", 5)) {
			printf("set_mic_mute: %d\n", dev->set_mic_mute(dev, strtoul(a, 0, 0) != 0));
		} else if (!strncmp(line, "open ", 5)) {
			char *p = a;
			uint32_t d = strtoul(p, &p, 16), f = strtoul(p, &p, 16);
			uint32_t rate = strtoul(p, &p, 10), ch = strtoul(p, &p, 10);
			struct audio_config c = { 0 };
			c.sample_rate = rate ? rate : 48000;
			c.channel_mask = ch == 1 ? 0x1 : 0x3; /* MONO / STEREO */
			c.format = 0x1; /* PCM_16_BIT */
			c.offload_info.version = 0x0201;
			c.offload_info.size = sizeof c.offload_info;
			if (out) { dev->close_output_stream(dev, out); out = 0; }
			r = dev->open_output_stream(dev, 13, d, f, &c, &out, "");
			printf("open_output_stream: %d rate %u ch %x fmt %x\n", r, c.sample_rate,
			       c.channel_mask, c.format);
			if (r) out = 0;
			else printf("buffer %u byte, latenza %u ms\n",
				    (unsigned)out->common.get_buffer_size(&out->common),
				    out->get_latency(out));
		} else if (!strncmp(line, "oparam ", 7)) {
			printf("stream set_parameters: %d\n",
			       out ? out->common.set_parameters(&out->common, a) : -1);
		} else if (!strncmp(line, "play ", 5)) {
			int fd = open(a, 0);
			static char buf[8192];
			ssize_t k, tot = 0;
			if (fd < 0 || !out) { printf("play: errore\n"); continue; }
			size_t bs = out->common.get_buffer_size(&out->common);
			if (bs > sizeof buf) bs = sizeof buf;
			while ((k = read(fd, buf, bs)) > 0) {
				ssize_t w = out->write(out, buf, k);
				if (w < 0) { printf("write: %d\n", (int)w); break; }
				tot += w;
			}
			close(fd);
			printf("play: %d byte\n", (int)tot);
		} else if (!strncmp(line, "close", 5)) {
			if (out) dev->close_output_stream(dev, out);
			out = 0;
			printf("chiuso\n");
		} else if (!strncmp(line, "patch ", 6)) {
			char *p = a;
			struct audio_port_config src = { 0 }, sink = { 0 };
			int h = 0;
			port_device(&src, 1, strtoul(p, &p, 16));
			port_device(&sink, 2, strtoul(p, &p, 16));
			r = dev->create_audio_patch(dev, 1, &src, 1, &sink, &h);
			keep_patch(r, h);
			printf("create_audio_patch %x->%x: %d handle %d\n", src.ext.device.type,
			       sink.ext.device.type, r, h);
		} else if (!strncmp(line, "mixpatch ", 9)) {
			struct audio_port_config src = { 0 }, sink = { 0 };
			int h = 0;
			src.role = 1; src.type = 2; /* sorgente: mix (stream di uscita) */
			src.ext.mix.hw_module = 10; src.ext.mix.handle = 13;
			port_device(&sink, 2, strtoul(a, 0, 16));
			r = dev->create_audio_patch(dev, 1, &src, 1, &sink, &h);
			keep_patch(r, h);
			printf("create_audio_patch mix->%x: %d handle %d\n", sink.ext.device.type, r, h);
		} else if (!strncmp(line, "unpatchall", 10)) {
			while (npatches > 0) {
				int h = patches[--npatches];
				printf("release_audio_patch %d: %d\n", h, dev->release_audio_patch(dev, h));
			}
		} else if (!strncmp(line, "unpatch ", 8)) {
			printf("release_audio_patch: %d\n", dev->release_audio_patch(dev, (int)strtoul(a, 0, 0)));
		} else if (!strncmp(line, "mopen ", 6)) {
			char *p = a;
			uint32_t rate = strtoul(p, &p, 10), ch = strtoul(p, &p, 10);
			if (music) dev->close_output_stream(dev, music);
			music = open_out(14, 0x10000, 0x10000, rate, ch);
		} else if (!strncmp(line, "mplay ", 6)) {
			play(music, a);
		} else if (!strncmp(line, "mclose", 6)) {
			if (music) dev->close_output_stream(dev, music);
			music = 0;
			printf("chiuso\n");
		} else if (!strncmp(line, "iopen ", 6)) {
			char *p = a;
			uint32_t d = strtoul(p, &p, 16), src = strtoul(p, &p, 10);
			uint32_t rate = strtoul(p, &p, 10), ch = strtoul(p, &p, 10);
			struct audio_config c = { 0 };
			c.sample_rate = rate ? rate : 16000;
			c.channel_mask = ch == 2 ? 0xc : 0x10; /* IN_STEREO / IN_MONO */
			c.format = 0x1;
			if (in) { dev->close_input_stream(dev, in); in = 0; }
			r = dev->open_input_stream(dev, 20, d, &c, &in, 0, "", src);
			printf("open_input_stream(%x, sorgente %u): %d rate %u ch %x fmt %x\n", d, src, r,
			       c.sample_rate, c.channel_mask, c.format);
			if (r) in = 0;
			else printf("buffer %u byte\n", (unsigned)in->common.get_buffer_size(&in->common));
		} else if (!strncmp(line, "rec ", 4)) {
			char *p = a, *path = a;
			while (*p && *p != ' ') p++;
			if (*p) *p++ = 0;
			double secs = strtod(p, 0);
			if (!in) { printf("rec: stream di ingresso chiuso\n"); continue; }
			int fd = open(path, 0x241 /* O_WRONLY|O_CREAT|O_TRUNC */, 0644);
			static char buf[8192];
			size_t bs = in->common.get_buffer_size(&in->common);
			if (bs > sizeof buf) bs = sizeof buf;
			unsigned rate = in->common.get_sample_rate(&in->common);
			unsigned chm = in->common.get_channels(&in->common);
			size_t want = (size_t)(secs * rate * 2 * (chm == 0xc ? 2 : 1)), tot = 0;
			long peak = 0;
			while (tot < want) {
				ssize_t k = in->read(in, buf, bs);
				if (k <= 0) { printf("read: %d\n", (int)k); break; }
				for (ssize_t i = 0; i + 1 < k; i += 2) {
					long v = (short)((unsigned char)buf[i] | (buf[i + 1] << 8));
					if (v < 0) v = -v;
					if (v > peak) peak = v;
				}
				if (fd >= 0) write(fd, buf, k);
				tot += k;
			}
			if (fd >= 0) close(fd);
			printf("rec: %u byte, rate %u, picco %ld\n", (unsigned)tot, rate, peak);
		} else if (!strncmp(line, "recvad ", 7)) {
			char *p = a, *path = a;
			while (*p && *p != ' ') p++;
			if (*p) *p++ = 0;
			double maxs = strtod(p, &p);
			unsigned sil_ms = strtoul(p, &p, 10), thr = strtoul(p, &p, 10);
			if (!sil_ms) sil_ms = 900;
			if (!thr) thr = 700;
			if (!in) { printf("recvad: stream di ingresso chiuso\n"); continue; }
			unsigned rate = in->common.get_sample_rate(&in->common);
			/* frame da 20 ms, mono 16 bit */
			size_t fb = rate / 50 * 2, tot = 0, maxb = (size_t)(maxs * rate * 2), quiet = 0;
			static short fr[4800];
			if (fb > sizeof fr) fb = sizeof fr;
			int fd = open(path, 0x241, 0644), spoke = 0;
			while (tot < maxb) {
				ssize_t k = in->read(in, fr, fb);
				if (k <= 0) { printf("read: %d\n", (int)k); break; }
				double e = 0;
				for (ssize_t i = 0; i < k / 2; i++) e += (double)fr[i] * fr[i];
				/* RMS >= soglia, confrontando i quadrati */
				if (e / (k / 2) >= (double)thr * thr) { spoke = 1; quiet = 0; } else if (spoke) quiet += 20;
				if (spoke && fd >= 0) write(fd, fr, k);
				tot += k;
				if (spoke && quiet >= sil_ms) break;
			}
			if (fd >= 0) close(fd);
			printf("recvad: %u byte parlato %d\n", (unsigned)tot, spoke);
		} else if (!strncmp(line, "iclose", 6)) {
			if (in) dev->close_input_stream(dev, in);
			in = 0;
			printf("chiuso\n");
		} else if (!strncmp(line, "sleep ", 6)) {
			usleep((unsigned)(strtod(a, 0) * 1e6));
			printf("ok\n");
		} else if (!strncmp(line, "quit", 4)) {
			break;
		} else if (n) {
			printf("comando sconosciuto: %s\n", line);
		}
	}
	if (in) dev->close_input_stream(dev, in);
	if (music) dev->close_output_stream(dev, music);
	if (out) dev->close_output_stream(dev, out);
	dev->common.close(&dev->common);
	return 0;
}
