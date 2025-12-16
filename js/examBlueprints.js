export const EXAM_BLUEPRINTS = {
  ssc: {
    refresh: "daily",
    sections: [
      { subject: "reasoning", count: 7 },
      { subject: "quant", count: 7 },
      { subject: "science", count: 5 },
      { subject: "current-affairs", count: 6 }
    ]
  },

  bank: {
    refresh: "daily",
    sections: [
      { subject: "reasoning", count: 10 },
      { subject: "quant", count: 10 },
      { subject: "computer", count: 5 }
    ]
  },

  rrb: {
    refresh: "weekly",
    sections: [
      { subject: "reasoning", count: 8 },
      { subject: "science", count: 7 },
      { subject: "current-affairs", count: 5 },
      { subject: "static-gk", count: 5 }
    ]
  },

  psc: {
    refresh: "weekly",
    sections: [
      { subject: "static-gk", count: 10 },
      { subject: "science", count: 7 },
      { subject: "current-affairs", count: 8 }
    ]
  },

  cuet: {
    refresh: "daily",
    sections: [
      { subject: "current-affairs", count: 8 },
      { subject: "reasoning", count: 7 },
      { subject: "science", count: 5 },
      { subject: "static-gk", count: 5 }
    ]
  },

  upsc: {
    refresh: "daily",
    sections: [
      { subject: "current-affairs", count: 10 },
      { subject: "static-gk", count: 8 },
      { subject: "science", count: 5 },
      { subject: "reasoning", count: 2 }
    ]
  },

  mixed: {
    refresh: "daily",
    sections: [
      { subject: "reasoning", count: 5 },
      { subject: "quant", count: 5 },
      { subject: "science", count: 5 },
      { subject: "computer", count: 5 },
      { subject: "current-affairs", count: 5 }
    ]
  }
};
