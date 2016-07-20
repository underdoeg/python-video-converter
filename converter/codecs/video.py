#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import BaseCodec


class VideoCodec(BaseCodec):

    """
    Base video codec class handles general video options. Possible
    parameters are:
      * codec (string) - video codec name
      * bitrate (string) - stream bitrate
      * max_bitrate (string) - maximum stream bitrate
      * fps (integer) - frames per second
      * keyframe_interval (integer) - keyframe interval
      * width (integer) - video width
      * height (integer) - video height
      * mode (string) - aspect preserval mode; one of:
            * stretch (default) - don't preserve aspect
            * crop - crop extra w/h
            * pad - pad with black bars
      * src_width (int) - source width
      * src_height (int) - source height

    Aspect preserval mode is only used if both source
    and both destination sizes are specified. If source
    dimensions are not specified, aspect settings are ignored.

    If source dimensions are specified, and only one
    of the destination dimensions is specified, the other one
    is calculated to preserve the aspect ratio.

    Supported video codecs are: null (no video), copy (copy directly
    from the source), Theora, H.264/AVC, DivX, VP8, H.263, Flv,
    MPEG-1, MPEG-2, WMV.
    """

    codec_type = "video"
    encoder_options = {
        'codec': str,
        'bitrate': int,
        'max_bitrate': int,
        'fps': int,
        'keyframe_interval': int,
        'width': int,
        'height': int,
        'mode': str,
        'src_width': int,
        'src_height': int,
    }

    def _aspect_corrections(self, sw, sh, w, h, mode):
        # If we don't have source info, we don't try to calculate
        # aspect corrections
        if not sw or not sh:
            return w, h, None

        # Original aspect ratio
        aspect = (1.0 * sw) / (1.0 * sh)

        # If we have only one dimension, we can easily calculate
        # the other to match the source aspect ratio
        if not w and not h:
            return w, h, None
        elif w and not h:
            h = int((1.0 * w) / aspect)
            return w, h, None
        elif h and not w:
            w = int(aspect * h)
            return w, h, None

        # If source and target dimensions are actually the same aspect
        # ratio, we've got nothing to do
        if int(aspect * h) == w:
            return w, h, None

        if mode == 'stretch':
            return w, h, None

        target_aspect = (1.0 * w) / (1.0 * h)

        if mode == 'crop':
            # source is taller, need to crop top/bottom
            if target_aspect > aspect:  # target is taller
                h0 = int(w / aspect)
                assert h0 > h, (sw, sh, w, h)
                dh = (h0 - h) / 2
                return w, h0, 'crop=%d:%d:0:%d' % (w, h, dh)
            else:  # source is wider, need to crop left/right
                w0 = int(h * aspect)
                assert w0 > w, (sw, sh, w, h)
                dw = (w0 - w) / 2
                return w0, h, 'crop=%d:%d:%d:0' % (w, h, dw)

        if mode == 'pad':
            # target is taller, need to pad top/bottom
            if target_aspect < aspect:
                h1 = int(w / aspect)
                assert h1 < h, (sw, sh, w, h)
                dh = (h - h1) / 2
                return w, h1, 'pad=%d:%d:0:%d' % (w, h, dh)  # FIXED
            else:  # target is wider, need to pad left/right
                w1 = int(h * aspect)
                assert w1 < w, (sw, sh, w, h)
                dw = (w - w1) / 2
                return w1, h, 'pad=%d:%d:%d:0' % (w, h, dw)  # FIXED

        assert False, mode

    def parse_options(self, opt):
        super(VideoCodec, self).parse_options(opt)

        safe = self.safe_options(opt)

        if 'fps' in safe:
            f = safe['fps']
            if f < 1 or f > 120:
                del safe['fps']

        if 'keyframe_interval' in safe:
            ki = safe['keyframe_interval']
            if ki < 1 or ki > 1500:
                del safe['keyframe_interval']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 16 or br > 15000:
                del safe['bitrate']

        if 'max_bitrate' in safe:
            mb = safe['max_bitrate']
            if mb < 16 or mb > 15000:
                del safe['max_bitrate']

        w = None
        h = None

        if 'width' in safe:
            w = safe['width']
            if w < 16 or w > 4000:
                w = None

        if 'height' in safe:
            h = safe['height']
            if h < 16 or h > 3000:
                h = None

        sw = None
        sh = None

        if 'src_width' in safe and 'src_height' in safe:
            sw = safe['src_width']
            sh = safe['src_height']
            if not sw or not sh:
                sw = None
                sh = None

        mode = 'stretch'
        if 'mode' in safe:
            if safe['mode'] in ('stretch', 'crop', 'pad'):
                mode = safe['mode']

        ow, oh = w, h  # FIXED
        w, h, filters = self._aspect_corrections(sw, sh, w, h, mode)

        safe['width'] = w
        safe['height'] = h
        safe['aspect_filters'] = filters

        if w and h:
            safe['aspect'] = '%d:%d' % (w, h)

        safe = self._codec_specific_parse_options(safe)

        w = safe['width']
        h = safe['height']
        filters = safe['aspect_filters']

        optlist = ['-vcodec', self.ffmpeg_codec_name]
        if 'fps' in safe:
            optlist.extend(['-r', str(safe['fps'])])
        if 'keyframe_interval' in safe:
            optlist.extend(['-g', str(safe['keyframe_interval'])])
        if 'bitrate' in safe:
            optlist.extend(['-vb', str(safe['bitrate']) + 'k'])  # FIXED
        if 'max_bitrate' in safe:
            optlist.extend(['-maxrate', str(safe['max_bitrate']) + 'k', '-bufsize', str(safe['max_bitrate']) + 'k'])
        if w and h:
            optlist.extend(['-s', '%dx%d' % (w, h)])

            if ow and oh:
                optlist.extend(['-aspect', '%d:%d' % (ow, oh)])

        if filters:
            optlist.extend(['-vf', filters])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class VideoNullCodec(VideoCodec):

    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-vn']


class VideoCopyCodec(VideoCodec):

    """
    Copy video stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-vcodec', 'copy']


class TheoraCodec(VideoCodec):

    """
    Theora video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'theora'
    ffmpeg_codec_name = 'libtheora'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 5-7 is a good range to try (default is 200k bitrate)
    })

    def _codec_specific_parse_options(self, safe):
        if 'quality' in safe:
            q = safe['quality']
            if q < 0 or q > 10:
                del safe['quality']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', str(safe['quality'])])
        return optlist


class H264Codec(VideoCodec):

    """
    H.264/AVC video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/x264EncodingGuide
    """
    codec_name = 'h264'
    ffmpeg_codec_name = 'libx264'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'quality': int,  # constant rate factor, range:0(lossless)-51(worst)
        # default:23, recommended: 18-28
        # http://mewiki.project357.com/wiki/X264_Settings#profile
        'profile': str,  # default: not-set, for valid values see above link
        'tune': str,  # default: not-set, for valid values see above link
    })

    def _codec_specific_parse_options(self, safe):
        if 'quality' in safe:
            q = safe['quality']
            if q < 0 or q > 51:
                del safe['quality']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'quality' in safe:
            optlist.extend(['-crf', str(safe['quality'])])
        if 'profile' in safe:
            optlist.extend(['-profile', safe['profile']])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        return optlist

class VaapiH264Codec(VideoCodec):

    """
    H.264/AVC video codec.
    @see https://wiki.libav.org/Hardware/vaapi#H.264
    """
    codec_name = 'h264_vaapi'
    ffmpeg_codec_name = 'h264_vaapi'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'quality': int,  # constant rate factor, range:0(lossless)-51(worst)
        # default:23, recommended: 18-28
        'profile': str,  # default: not-set, for valid values see above link
    })

    def _codec_specific_parse_options(self, safe):
        if 'quality' in safe:
            q = safe['quality']
            if q < 0 or q > 51:
                del safe['quality']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        # ffmpeg must run with -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -hwaccel_output_format vaapi before -i
        optlist.extend(['-vf', 'format=nv12|vaapi,hwupload'])
        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'quality' in safe:
            optlist.extend(['-crf', str(safe['quality'])])
        if 'profile' in safe:
            optlist.extend(['-profile', safe['profile']])
        return optlist

class DivxCodec(VideoCodec):

    """
    DivX video codec.
    """
    codec_name = 'divx'
    ffmpeg_codec_name = 'mpeg4'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # quality, range:1(lossless)-31(worst)
        # 2 is visually lossless. Doubling the value results in half the bitrate.
        # recommended: 3-5, http://slhck.info/video-encoding
    })

    def _codec_specific_parse_options(self, safe):
        if 'quality' in safe:
            q = safe['quality']
            if q < 1 or q > 31:
                del safe['quality']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', str(safe['quality'])])
        return optlist


class Vp8Codec(VideoCodec):

    """
    Google VP8 video codec.
    """
    codec_name = 'vp8'
    ffmpeg_codec_name = 'libvpx'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # quality, range:0(lossless)-63(worst)
        # recommended: 10, http://slhck.info/video-encoding
        'threads': int,  # threads number
        # default: 1, recommended: number of real cores - 1
    })

    def _codec_specific_parse_options(self, safe):
        if 'quality' in safe:
            q = safe['quality']
            if q < 0 or q > 63:
                del safe['quality']
        if 'threads' in safe:
            t = safe['threads']
            if t < 1:
                del safe['threads']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-crf', str(safe['quality'])])
            if 'max_bitrate' in safe:
                optlist.extend(['-vb', str(safe['max_bitrate']) + 'k'])
        if 'threads' in safe:
            optlist.extend(['-threads', str(safe['threads'])])
        return optlist


class H263Codec(VideoCodec):

    """
    H.263 video codec.
    """
    codec_name = 'h263'
    ffmpeg_codec_name = 'h263'


class FlvCodec(VideoCodec):

    """
    Flash Video codec.
    """
    codec_name = 'flv'
    ffmpeg_codec_name = 'flv'


class MpegCodec(VideoCodec):

    """
    Base MPEG video codec.
    """
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # quality, range:1(lossless)-31(worst)
        # 2 is visually lossless. Doubling the value results in half the bitrate.
        # recommended: 3-5, http://slhck.info/video-encoding
    })

    # Workaround for a bug in ffmpeg in which aspect ratio
    # is not correctly preserved, so we have to set it
    # again in vf; take care to put it *before* crop/pad, so
    # it uses the same adjusted dimensions as the codec itself
    # (pad/crop will adjust it further if neccessary)
    def _codec_specific_parse_options(self, safe):
        w = safe['width']
        h = safe['height']

        if w and h:
            filters = safe['aspect_filters']
            tmp = 'aspect=%d:%d' % (w, h)

            if filters is None:
                safe['aspect_filters'] = tmp
            else:
                safe['aspect_filters'] = tmp + ',' + filters

        if 'quality' in safe:
            q = safe['quality']
            if q < 1 or q > 31:
                del safe['quality']

        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', str(safe['quality'])])
        return optlist


class Mpeg1Codec(MpegCodec):

    """
    MPEG-1 video codec.
    """
    codec_name = 'mpeg1'
    ffmpeg_codec_name = 'mpeg1video'


class Mpeg2Codec(MpegCodec):

    """
    MPEG-2 video codec.
    """
    codec_name = 'mpeg2'
    ffmpeg_codec_name = 'mpeg2video'


class WmvCodec(VideoCodec):

    """
    WMV video codec.
    """
    codec_name = 'wmv'
    ffmpeg_codec_name = 'msmpeg4'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # quality, range:1(lossless)-31(worst)
        # 2 is visually lossless. Doubling the value results in half the bitrate.
        # recommended: 3-5, http://slhck.info/video-encoding
    })

    def _codec_specific_parse_options(self, safe):
        if 'quality' in safe:
            q = safe['quality']
            if q < 1 or q > 31:
                del safe['quality']

        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', str(safe['quality'])])
        return optlist
