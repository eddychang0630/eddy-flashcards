import { speakingGuides } from './speaking-guides.mjs';

export function renderSpeakingGuides(container) {
  const document = container.ownerDocument;
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function renderPattern(pattern) {
    const card = element('article', '', 'guide-pattern');
    card.append(
      element('h4', pattern.title),
      element('p', pattern.usage, 'guide-usage'),
      element('span', '句型', 'field-label'),
      element('p', pattern.structure, 'guide-structure'),
    );

    const examples = element('ul', '', 'guide-examples');
    for (const [english, chinese] of pattern.examples) {
      const example = element('li');
      const original = element('p', english, 'guide-example-en');
      original.lang = 'en';
      example.append(original, element('p', chinese, 'guide-example-zh'));
      examples.append(example);
    }
    card.append(element('span', '例句', 'field-label'), examples);

    const correction = element('div', '', 'guide-correction');
    const wrong = element('p', pattern.mistake.wrong, 'guide-wrong');
    const right = element('p', pattern.mistake.right, 'guide-right');
    wrong.lang = right.lang = 'en';
    const wrongLabel = element('span', '常見錯誤', 'field-label');
    const rightLabel = element('span', '正確說法', 'field-label');
    correction.append(wrongLabel, wrong, rightLabel, right, element('p', pattern.mistake.reason, 'guide-correction-note'));
    card.append(correction);
    return card;
  }

  const topicPanel = element('article', '', 'guide-topic');
  container.replaceChildren(topicPanel);

  function showTopic(topic) {
    const sections = new Map();
    const content = element('div', '', 'guide-sections');
    for (const section of topic.sections) {
      const details = element('details', '', 'guide-section');
      details.id = 'guide-' + topic.id + '-' + section.id;
      const summary = element('summary');
      const heading = element('div');
      heading.append(element('h3', section.title), element('p', section.description));
      summary.append(heading);
      const patterns = element('div', '', 'guide-patterns');
      for (const pattern of section.patterns) patterns.append(renderPattern(pattern));
      details.append(summary, patterns);
      sections.set(section.id, { details, summary });
      content.append(details);
    }

    const map = element('section', '', 'guide-map');
    const shortcuts = element('div', '', 'guide-shortcuts');
    for (const shortcut of topic.shortcuts) {
      const target = sections.get(shortcut.section);
      const button = element('button', '', 'guide-shortcut');
      button.type = 'button';
      button.setAttribute('aria-controls', target.details.id);
      const opening = element('strong', shortcut.opening);
      opening.lang = 'en';
      button.append(element('span', shortcut.label), opening);
      button.addEventListener('click', () => {
        target.details.open = true;
        target.details.scrollIntoView({ block: 'start' });
        target.summary.focus({ preventScroll: true });
      });
      shortcuts.append(button);
    }
    map.append(element('h3', '快速開口'), shortcuts);
    topicPanel.replaceChildren(element('h2', topic.title), element('p', topic.introduction, 'guide-intro'), map, content);
  }

  if (speakingGuides.length > 1) {
    const label = element('label', '主題', 'guide-topic-picker');
    const select = element('select');
    for (const topic of speakingGuides) {
      const option = element('option', topic.title);
      option.value = topic.id;
      select.append(option);
    }
    select.addEventListener('change', () => showTopic(speakingGuides[select.selectedIndex]));
    label.append(select);
    container.replaceChildren(label, topicPanel);
  }
  showTopic(speakingGuides[0]);
}
