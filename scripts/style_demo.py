"""Add editable motion graphics to the recorded app, without simulating features."""
import json
import subprocess
from pathlib import Path

from scripts.record_demo import ass_time


def main():
    output = Path(__file__).resolve().parents[1]/'output'/'demo'
    receipt = json.loads((output/'receipt.json').read_text())
    styles = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1440
PlayResY: 810
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,25,&H00FFFFFF,&H00FFFFFF,&H0021382B,&H0021382B,0,0,0,0,100,100,0,0,1,0,0,2,60,60,18,1
Style: Motion,Arial,24,&H00FFFFFF,&H00FFFFFF,&H0021382B,&H0021382B,0,0,0,0,100,100,0,0,1,0,0,5,40,40,20,1
Style: Callout,Arial,19,&H00FFFFFF,&H00FFFFFF,&H0021382B,&H0021382B,0,0,0,0,100,100,0,0,3,9,0,5,40,40,20,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    def event(start,end,style,text):
        return f'Dialogue: 1,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}\n'
    for scene in receipt['scenes']:
        words=scene['text'].replace('\n',r'\N')
        styles += event(scene['start'],scene['end'],'Caption',r'{\fad(200,140)\fs13\c&HAFEFD8&}'+scene['title']+r'{\fs25\c&HFFFFFF&}\N'+words)
    styles += event(.15,3.65,'Motion',r'{\fad(450,300)\fnGeorgia\fs72\move(720,280,720,255,0,500)}SecondShape.')
    styles += event(.45,3.65,'Motion',r'{\fad(450,300)\pos(720,330)\fs18\fsp3\c&HAFEFD8&}LET THE OFFCUT HAVE A SAY')
    for start,x,text in [(.8,365,'YOUR OFFCUTS'),(1.2,720,'A FLEXIBLE BRIEF'),(1.6,1075,'A SECOND LIFE')]:
        styles += event(start,3.65,'Callout',r'{\fad(400,250)\move('+f'{x},455,{x},435,0,400'+r')\fs22}'+text)
    styles += event(1.1,3.65,'Motion',r'{\fad(350,250)\pos(542,435)\fs33\c&HAFEFD8&}→')
    styles += event(1.5,3.65,'Motion',r'{\fad(350,250)\pos(895,435)\fs33\c&HAFEFD8&}→')
    for index,label,x,y in [(2,'40 mm OF FLEXIBILITY',1185,275),(3,'DEFECTS CHANGE THE ANSWER',1100,277),(4,'ALL FIVE PARTS REMAIN REQUIRED',870,550),(6,'BRIEF + INVENTORY + COORDINATES',1050,285)]:
        scene=receipt['scenes'][index]
        styles += event(scene['start']+.5,min(scene['end']-.3,scene['start']+4.6),'Callout',r'{\fad(250,250)\move('+f'{x},{y+12},{x},{y},0,300'+r')}'+label)
    (output/'motion.ass').write_text(styles)
    final=output/'secondshape-motion-silent.mp4'
    filters=f"drawbox=x=0:y=0:w=iw:h=ih:color=0x173a2b@0.96:t=fill:enable='lt(t,3.7)',drawbox=x=0:y=704:w=iw:h=106:color=0x21382b:t=fill,ass={output}/motion.ass"
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(output/'secondshape-demo.mp4'),'-vf',filters,'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-an','-movflags','+faststart',str(final)],check=True)
    print(final)


if __name__=='__main__':
    main()
