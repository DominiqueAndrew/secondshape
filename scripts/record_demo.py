"""Record real browser interactions and add original, silent English captions."""
import argparse
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def ass_time(seconds):
    cs = round(seconds*100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'


def srt_time(seconds):
    ms = round(seconds*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8767')
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1]/'output'/'demo'
    output.mkdir(parents=True,exist_ok=True)
    scenes = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={'width':1440,'height':810},device_scale_factor=1,record_video_dir=str(output),record_video_size={'width':1440,'height':810})
        started = time.perf_counter()
        page = context.new_page()
        video = page.video
        page.goto(args.url,wait_until='networkidle')
        expect(page.locator('#state-pill')).to_have_text('✓ Geometry checked',timeout=30000)
        beginning = time.perf_counter()
        trim = beginning-started

        def scene(title,text,seconds):
            scenes.append({'start':time.perf_counter()-beginning,'title':title,'text':text})
            print(title,flush=True)
            page.wait_for_timeout(seconds*1000)

        def workspace():
            page.locator('.workspace').evaluate('(el)=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-15,behavior:"smooth"})')
            page.wait_for_timeout(700)

        scene('01 / A MATERIAL-FIRST BRIEF','What if a good offcut could change the design\nbefore you bought another panel?',6)
        workspace()
        page.get_by_role('tab',name='Fixed brief',exact=True).click()
        expect(page.locator('#metric-new')).to_have_text('1')
        scene('02 / THE COUNTERFACTUAL','The fixed 600 × 240 mm brief uses one new panel\nin this heuristic plan. The original parts are all retained.',7)
        page.get_by_role('tab',name='Second shape',exact=True).click()
        expect(page.locator('#metric-change')).to_have_text('−40 mm')
        scene('03 / THE SECOND SHAPE','Accept 40 mm less width: Python fits all five parts\nonto two existing panels, around the damaged edge.',8)
        page.get_by_role('button',name='1 defect · clear',exact=True).click()
        page.locator('#solve-button').click()
        expect(page.locator('#metric-change')).to_have_text('−10 mm',timeout=30000)
        workspace()
        scene('04 / CHALLENGE THE INPUT','Remove the defect in this what-if case, and the\nclosest sampled width changes to 590 mm. Geometry matters.',8)
        page.locator('#reset').click()
        expect(page.locator('#state-pill')).to_have_text('✓ Geometry checked',timeout=30000)
        page.locator('#min-width').fill('600')
        page.locator('#min-depth').fill('240')
        page.locator('#solve-button').click()
        expect(page.locator('#state-pill')).to_have_text('No salvage fit found',timeout=30000)
        workspace()
        scene('05 / KEEP FAILURE VISIBLE','No dimension concession? No salvage fit found.\nThe planner refuses to drop a part or break your brief.',8)
        page.get_by_role('tab',name='Fixed brief',exact=True).click()
        expect(page.locator('#metric-new')).to_have_text('1')
        scene('06 / A SEPARATE BASELINE','The fixed-brief comparison still works.\nA failed salvage search is not a failed purchased-stock plan.',6)
        page.locator('#reset').click()
        expect(page.locator('#state-pill')).to_have_text('✓ Geometry checked',timeout=30000)
        page.locator('#evidence').evaluate('(el)=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-180,behavior:"smooth"})')
        page.get_by_role('button',name='Recheck geometry').click()
        expect(page.locator('#verify-status')).to_contain_text('Verified again',timeout=10000)
        with page.expect_download() as download:
            page.locator('#download').click()
        download.value.save_as(output/'recorded-proof.json')
        scene('07 / MAKE THE CLAIM CHECKABLE','Export the brief, inventory, five mandatory parts and coordinates.\nA separate verifier checks geometry and input provenance.',8)
        page.locator('#evidence').evaluate('(el)=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-40,behavior:"smooth"})')
        scene('08 / HONEST EVIDENCE','Illustrative inventory: 0.7442 m² less purchased panel area,\nwith 4.3% less part area. No carbon or field-impact claim.',8)
        page.evaluate('window.scrollTo({top:0,behavior:"smooth"})')
        scene('SECONDSHAPE','Design back from what already exists.\nPython. Open source. Reproducible.',5)
        duration = time.perf_counter()-beginning
        page.close()
        context.close()
        raw = Path(video.path())
        browser.close()
    for i,scene in enumerate(scenes):
        scene['end'] = scenes[i+1]['start'] if i+1<len(scenes) else duration
    ass = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1440
PlayResY: 810
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,26,&H00FFFFFF,&H00FFFFFF,&HE021382B,&HE021382B,0,0,0,0,100,100,0,0,3,12,0,2,70,70,23,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    srt = ''
    for i,scene in enumerate(scenes):
        text = scene['text'].replace('\n',r'\N')
        title = scene['title']
        ass += f"Dialogue: 0,{ass_time(scene['start'])},{ass_time(scene['end'])},Caption,,0,0,0,,{{\\fad(240,160)\\fs14\\c&HAAE9D8&}}{title}{{\\fs26\\c&HFFFFFF&}}\\N{text}\n"
        srt += f"{i+1}\n{srt_time(scene['start'])} --> {srt_time(scene['end'])}\n{title}\n{scene['text']}\n\n"
    (output/'captions.ass').write_text(ass)
    (output/'captions.srt').write_text(srt)
    final = output/'secondshape-demo.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(trim),'-i',str(raw),'-t',str(duration),'-vf',f'ass={output}/captions.ass','-r','24','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(final)],check=True)
    receipt = {'url':args.url,'video':str(final),'source_recording':str(raw),'duration_seconds':duration,'viewport':{'width':1440,'height':810},'media':'Real Playwright browser recording with original English captions and restrained caption fades. No voice, music, stock footage or generative media.','scenes':scenes}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'video':str(final),'duration_seconds':duration}),flush=True)


if __name__ == '__main__':
    main()
