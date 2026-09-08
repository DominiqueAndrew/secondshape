"""Exercise the real UI and record responsive screenshot/overflow evidence."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

VIEWPORTS = [('mobile',390,844),('tablet',768,1024),('laptop',1366,768),('desktop',1440,900),('large',1920,1080),('wide',2560,1440)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8767')
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / 'output' / 'playwright'
    output.mkdir(parents=True, exist_ok=True)
    report = {'url':args.url,'device_scale_factor':1,'screenshots':[],'browser_errors':[],'flows':[]}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for name, width, height in VIEWPORTS:
            context = browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
            page = context.new_page()
            page.on('pageerror',lambda error: report['browser_errors'].append(str(error)))

            def capture(state, selector=None):
                if selector:
                    page.locator(selector).evaluate('(el) => window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY-18,behavior:"instant"})')
                geometry = page.evaluate('''() => ({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,clippedControls:[...document.querySelectorAll('button,input,textarea,select')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left < -1 || r.right > innerWidth+1}).map(e=>e.id||e.getAttribute('aria-label')||e.textContent.trim())})''')
                assert geometry['scrollWidth'] <= geometry['clientWidth']+1, (name,state,geometry)
                assert not geometry['clippedControls'], (name,state,geometry)
                filename = f'{name}-{width}x{height}-{state}.png'
                page.screenshot(path=str(output/filename),animations='disabled')
                report['screenshots'].append({'viewport':name,'width':width,'height':height,'state':state,'file':filename,**geometry})

            page.goto(args.url,wait_until='networkidle')
            expect(page.locator('#state-pill')).to_have_text('✓ Geometry checked',timeout=30000)
            expect(page.locator('#metric-parts')).to_have_text('5 / 5')
            expect(page.locator('#metric-change')).to_have_text('−40 mm')
            capture('initial')
            capture('salvage-layout','.workspace')
            page.get_by_role('tab',name='Fixed brief',exact=True).click()
            expect(page.locator('.new-badge')).to_be_visible()
            expect(page.locator('#metric-new')).to_have_text('1')
            capture('fixed-brief','.workspace')
            page.get_by_role('tab',name='Second shape',exact=True).click()
            page.get_by_role('button',name='Recheck geometry').click()
            expect(page.locator('#verify-status')).to_contain_text('Verified again',timeout=10000)
            capture('evidence','#evidence')
            with page.expect_download() as info:
                page.locator('#download').click()
            downloaded = info.value
            path = output/f'{name}-proof.json'
            downloaded.save_as(path)
            proof = json.loads(path.read_text())
            assert proof['certificate']['valid'] and len(proof['placements']) == 5
            page.locator('#min-width').fill('600')
            page.locator('#min-depth').fill('240')
            expect(page.locator('#download')).to_be_disabled()
            capture('stale-inputs','.workspace')
            page.locator('#solve-button').click()
            expect(page.locator('#state-pill')).to_have_text('No salvage fit found',timeout=30000)
            expect(page.locator('#metric-new')).to_have_text('—')
            capture('no-fit','.workspace')
            page.get_by_role('tab',name='Fixed brief',exact=True).click()
            expect(page.locator('#metric-new')).to_have_text('1')
            expect(page.locator('#result-heading')).to_have_text('The fixed brief uses new stock.')
            capture('fixed-brief-after-no-fit','.workspace')
            page.get_by_role('tab',name='Second shape',exact=True).click()
            page.locator('summary').click()
            page.locator('#inventory-json').fill('{ not valid JSON')
            page.locator('#apply-json').click()
            expect(page.locator('#error')).to_be_visible()
            capture('input-error','#inventory-json')
            page.locator('#reset').click()
            expect(page.locator('#state-pill')).to_have_text('✓ Geometry checked',timeout=30000)
            page.get_by_role('button',name='1 defect · clear',exact=True).click()
            page.locator('#solve-button').click()
            expect(page.locator('#metric-change')).to_have_text('−10 mm',timeout=30000)
            capture('defect-cleared','.workspace')
            page.get_by_role('button',name='Add an offcut',exact=True).click()
            assert page.locator('.board-card').count() == 3
            page.get_by_role('button',name='Remove Offcut 3',exact=True).click()
            assert page.locator('.board-card').count() == 2
            page.locator('#reset').click()
            expect(page.locator('#state-pill')).to_have_text('✓ Geometry checked',timeout=30000)
            expect(page.locator('#metric-change')).to_have_text('−40 mm')
            report['flows'].append({'viewport':name,'passed':['initial_solve','baseline','verify','proof_download','stale_export_block','no_fit','invalid_inventory','defect_changes_solution','add_remove_board']})
            context.close()
            print(f'{name} {width}x{height}: 9 flows passed; no horizontal overflow',flush=True)
        browser.close()
    assert not report['browser_errors'],report['browser_errors']
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Saved {len(report['screenshots'])} screenshots and report: {output/'report.json'}",flush=True)


if __name__ == '__main__':
    main()
