const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/gaoch/.claude/skills/pptx/scripts/html2pptx');
const path = require('path');

async function createPresentation() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = '高老师';
    pptx.title = '漫谈 Vibe Coding';
    pptx.subject = 'AI时代的科研开发范式转变';

    const slidesDir = path.join(__dirname, 'slides');
    const slideFiles = [
        'slide01.html',      // 封面
        'slide02.html',      // 结课安排
        'slide03.html',      // 内容回顾
        'slide04.html',      // Paper Digest项目
        'slide05-img.html',  // 开发过程截图
        'slide05.html',      // 数据科学思维
        'slide06.html',      // 职业展望
        'slide07.html',      // Token出海介绍
        'slide08-img.html',  // Token出海截图
        'slide09-img.html',  // Coding Plan截图
        'slide10-img.html',  // 价格对比截图
        'slide08.html',      // Claude Code配置
        'slide09.html'       // 结束页
    ];

    console.log('Creating presentation...');

    for (let i = 0; i < slideFiles.length; i++) {
        const slidePath = path.join(slidesDir, slideFiles[i]);
        console.log(`Processing slide ${i + 1}/${slideFiles.length}: ${slideFiles[i]}`);

        try {
            await html2pptx(slidePath, pptx);
            console.log(`  ✓ Slide ${i + 1} created successfully`);
        } catch (error) {
            console.error(`  ✗ Error creating slide ${i + 1}: ${error.message}`);
            throw error;
        }
    }

    const outputPath = path.join(__dirname, '漫谈VibeCoding-2026年4月.pptx');
    await pptx.writeFile({ fileName: outputPath });
    console.log(`\n✓ Presentation saved to: ${outputPath}`);
}

createPresentation().catch(error => {
    console.error('Error creating presentation:', error);
    process.exit(1);
});
